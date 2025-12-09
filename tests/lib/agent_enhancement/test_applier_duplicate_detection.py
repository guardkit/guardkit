"""
Tests for duplicate section detection in EnhancementApplier.

TASK-FIX-AE01: Test coverage for Finding 2 (duplicate content bug).
"""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

# Add the installer.global.lib.agent_enhancement directory to Python path
_test_dir = Path(__file__).resolve().parent
_lib_dir = _test_dir.parent.parent.parent / "installer" / "global" / "lib" / "agent_enhancement"
sys.path.insert(0, str(_lib_dir))

from applier import EnhancementApplier


class TestNormalizeSectionName:
    """Test _normalize_section_name() method."""

    def test_basic_lowercase(self):
        """Should convert to lowercase."""
        applier = EnhancementApplier()
        assert applier._normalize_section_name("Technologies") == "technologies"
        assert applier._normalize_section_name("TECHNOLOGIES") == "technologies"

    def test_underscore_to_space(self):
        """Should convert underscores to spaces."""
        applier = EnhancementApplier()
        assert applier._normalize_section_name("best_practices") == "best practices"
        assert applier._normalize_section_name("why_this_agent_exists") == "why this agent exists"

    def test_strip_whitespace(self):
        """Should strip leading/trailing whitespace."""
        applier = EnhancementApplier()
        assert applier._normalize_section_name("  technologies  ") == "technologies"
        assert applier._normalize_section_name("\ttechnologies\n") == "technologies"

    def test_combined_transformations(self):
        """Should handle combined case, underscore, and whitespace."""
        applier = EnhancementApplier()
        assert applier._normalize_section_name("  Why_This_Agent_Exists  ") == "why this agent exists"
        assert applier._normalize_section_name("BEST_PRACTICES") == "best practices"


class TestSectionExists:
    """Test _section_exists() fuzzy matching logic."""

    def test_exact_match_case_insensitive(self):
        """Should match exact header regardless of case."""
        applier = EnhancementApplier()
        content = "## Technologies\n\nContent here"

        assert applier._section_exists(content, "technologies")
        assert applier._section_exists(content, "Technologies")
        assert applier._section_exists(content, "TECHNOLOGIES")

    def test_underscore_normalization(self):
        """Should match headers with underscores converted to spaces."""
        applier = EnhancementApplier()
        content = "## Why This Agent Exists\n\nDescription"

        assert applier._section_exists(content, "why_this_agent_exists")
        assert applier._section_exists(content, "Why_This_Agent_Exists")

    def test_partial_match_existing_longer(self):
        """Should match when search term is substring of existing header."""
        applier = EnhancementApplier()
        content = "## Technologies Used\n\nList of tech"

        assert applier._section_exists(content, "technologies")

    def test_partial_match_search_longer(self):
        """Should match when existing header is substring of search term."""
        applier = EnhancementApplier()
        content = "## Technologies\n\nList of tech"

        assert applier._section_exists(content, "technologies_used")

    def test_no_match_different_section(self):
        """Should not match unrelated sections."""
        applier = EnhancementApplier()
        content = "## Code Examples\n\nExamples"

        assert not applier._section_exists(content, "technologies")
        assert not applier._section_exists(content, "best_practices")

    def test_multiple_sections_matches_correct_one(self):
        """Should match correct section among many."""
        applier = EnhancementApplier()
        content = """
## Quick Start

Instructions

## Technologies

List

## Best Practices

Guidelines
"""

        assert applier._section_exists(content, "technologies")
        assert applier._section_exists(content, "best_practices")
        assert not applier._section_exists(content, "anti_patterns")

    def test_header_without_space_after_hash(self):
        """Should match headers without space after ##."""
        applier = EnhancementApplier()
        content = "##Technologies\n\nContent"

        assert applier._section_exists(content, "technologies")

    def test_header_with_extra_spaces(self):
        """Should match headers with extra spaces."""
        applier = EnhancementApplier()
        content = "##   Technologies   \n\nContent"

        assert applier._section_exists(content, "technologies")

    def test_empty_content(self):
        """Should return False for empty content."""
        applier = EnhancementApplier()
        assert not applier._section_exists("", "technologies")

    def test_no_headers(self):
        """Should return False for content without headers."""
        applier = EnhancementApplier()
        content = "Just some text without any headers"
        assert not applier._section_exists(content, "technologies")

    def test_h3_headers_not_matched(self):
        """Should not match ### headers (only ##)."""
        applier = EnhancementApplier()
        content = "### Technologies\n\nSub-section content"

        # ### is not a ## section header
        assert not applier._section_exists(content, "technologies")


class TestMergeContentNoDuplicates:
    """Test that _merge_content() doesn't create duplicate sections."""

    def test_no_duplicate_when_section_exists(self):
        """Should not add section if similar header already exists."""
        applier = EnhancementApplier()

        original = """---
name: test-agent
---

# Test Agent

## Quick Start

Quick start content

## Technologies

Existing tech list
"""

        enhancement = {
            "sections": ["technologies"],
            "technologies": "## Technologies\n\nNew tech list"
        }

        result = applier._merge_content(original, enhancement)

        # Should NOT have duplicate Technologies section
        tech_count = result.count("## Technologies")
        assert tech_count == 1, f"Expected 1 Technologies section, found {tech_count}"

    def test_case_variation_no_duplicate(self):
        """Should not add section when only case differs."""
        applier = EnhancementApplier()

        original = """---
name: test-agent
---

# Test Agent

## TECHNOLOGIES

Existing content
"""

        enhancement = {
            "sections": ["technologies"],
            "technologies": "## Technologies\n\nNew content"
        }

        result = applier._merge_content(original, enhancement)

        # Count all ## headers to ensure no duplicate added
        headers = [line for line in result.split('\n') if line.strip().startswith('## ')]
        assert len(headers) == 1

    def test_partial_match_no_duplicate(self):
        """Should not add section when partial match exists."""
        applier = EnhancementApplier()

        original = """---
name: test-agent
---

# Test Agent

## Technologies Used

Existing list
"""

        enhancement = {
            "sections": ["technologies"],
            "technologies": "## Technologies\n\nNew list"
        }

        result = applier._merge_content(original, enhancement)

        # Should NOT add Technologies section (matches Technologies Used)
        assert result.count("## Technologies") == 1  # Only "Technologies Used"
        assert "## Technologies Used" in result  # Original preserved

    def test_adds_new_section_when_not_exists(self):
        """Should add section when it doesn't exist."""
        applier = EnhancementApplier()

        original = """---
name: test-agent
---

# Test Agent

## Quick Start

Content
"""

        enhancement = {
            "sections": ["best_practices"],
            "best_practices": "## Best Practices\n\n1. Do this\n2. Don't do that"
        }

        result = applier._merge_content(original, enhancement)

        assert "## Best Practices" in result
        assert "1. Do this" in result

    def test_multiple_sections_some_exist(self):
        """Should add only sections that don't exist."""
        applier = EnhancementApplier()

        original = """---
name: test-agent
---

# Test Agent

## Technologies

Existing
"""

        enhancement = {
            "sections": ["technologies", "best_practices"],
            "technologies": "## Technologies\n\nNew",
            "best_practices": "## Best Practices\n\nGuidelines"
        }

        result = applier._merge_content(original, enhancement)

        # Technologies should NOT be duplicated
        assert result.count("## Technologies") == 1
        # Best Practices should be added
        assert "## Best Practices" in result

    def test_underscore_variation_no_duplicate(self):
        """Should not add section when underscore variation exists."""
        applier = EnhancementApplier()

        original = """---
name: test-agent
---

# Test Agent

## Why This Agent Exists

Existing description
"""

        enhancement = {
            "sections": ["why_this_agent_exists"],
            "why_this_agent_exists": "## Why This Agent Exists\n\nNew description"
        }

        result = applier._merge_content(original, enhancement)

        # Should NOT duplicate the section
        assert result.count("## Why This Agent Exists") == 1
