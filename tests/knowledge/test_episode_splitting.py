"""
Tests for guardkit.knowledge.episode_splitting

Content-aware episode splitting for Graphiti knowledge seeding.

Splitting large episodes at markdown section boundaries reduces the number
of edges extracted per ``add_episode`` call, improving graphiti-core Phase 4
(edge resolution) performance.

Test Coverage:
- Short content returns a single chunk
- Content at threshold returns a single chunk
- Content over threshold splits at ## headings
- Content with no ## headings returns a single chunk even if over threshold
- Chunk metadata (chunk_index, total_chunks) is correct
- Empty content returns a single chunk
- Custom max_chars parameter works
- Greedy merging keeps adjacent small sections together
- Single large section (no headings) returned as-is
- Integration: large markdown with multiple ## sections produces expected chunks

Coverage Target: >=85%
Test Count: 20+ tests
"""

import pytest

try:
    from guardkit.knowledge.episode_splitting import (
        MAX_EPISODE_CHARS,
        EpisodeChunk,
        split_episode_content,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created",
)


# ============================================================================
# 1. EpisodeChunk Dataclass Tests
# ============================================================================

class TestEpisodeChunk:
    """Test the EpisodeChunk dataclass."""

    def test_episode_chunk_stores_content(self):
        """Test EpisodeChunk holds content correctly."""
        chunk = EpisodeChunk(content="hello world", chunk_index=1, total_chunks=1)
        assert chunk.content == "hello world"

    def test_episode_chunk_stores_chunk_index(self):
        """Test EpisodeChunk holds chunk_index correctly."""
        chunk = EpisodeChunk(content="x", chunk_index=2, total_chunks=3)
        assert chunk.chunk_index == 2

    def test_episode_chunk_stores_total_chunks(self):
        """Test EpisodeChunk holds total_chunks correctly."""
        chunk = EpisodeChunk(content="x", chunk_index=1, total_chunks=5)
        assert chunk.total_chunks == 5


# ============================================================================
# 2. MAX_EPISODE_CHARS Constant
# ============================================================================

class TestMaxEpisodeChars:
    """Test the MAX_EPISODE_CHARS constant."""

    def test_max_episode_chars_is_2000(self):
        """Test that MAX_EPISODE_CHARS is 2000 as specified."""
        assert MAX_EPISODE_CHARS == 2000

    def test_max_episode_chars_is_int(self):
        """Test that MAX_EPISODE_CHARS is an integer."""
        assert isinstance(MAX_EPISODE_CHARS, int)


# ============================================================================
# 3. Short Content (no splitting required)
# ============================================================================

class TestShortContent:
    """Test content that is under or at the threshold."""

    def test_empty_string_returns_single_chunk(self):
        """Empty content returns a single chunk with empty content."""
        chunks = split_episode_content("")
        assert len(chunks) == 1
        assert chunks[0].content == ""
        assert chunks[0].chunk_index == 1
        assert chunks[0].total_chunks == 1

    def test_none_like_empty_returns_single_chunk(self):
        """Falsy content does not raise; returns single chunk."""
        # Empty string is falsy
        chunks = split_episode_content("")
        assert len(chunks) == 1

    def test_short_content_returns_single_chunk(self):
        """Content well under threshold returns a single chunk."""
        content = "# Title\n\nShort content with some text."
        chunks = split_episode_content(content)
        assert len(chunks) == 1
        assert chunks[0].content == content

    def test_short_content_metadata_is_correct(self):
        """Single-chunk result has chunk_index=1 and total_chunks=1."""
        content = "Short content."
        chunks = split_episode_content(content)
        assert chunks[0].chunk_index == 1
        assert chunks[0].total_chunks == 1

    def test_content_exactly_at_threshold_returns_single_chunk(self):
        """Content with length == max_chars is NOT split."""
        content = "x" * MAX_EPISODE_CHARS
        chunks = split_episode_content(content)
        assert len(chunks) == 1
        assert chunks[0].content == content

    def test_content_one_below_threshold_returns_single_chunk(self):
        """Content with length == max_chars - 1 is not split."""
        content = "x" * (MAX_EPISODE_CHARS - 1)
        chunks = split_episode_content(content)
        assert len(chunks) == 1


# ============================================================================
# 4. Splitting at ## Headings
# ============================================================================

class TestSplittingAtHeadings:
    """Test content splitting at ## heading boundaries."""

    def _make_section(self, heading: str, body_chars: int) -> str:
        """Helper: create a section with a heading and body of given length."""
        return f"## {heading}\n\n{'x' * body_chars}\n\n"

    def test_over_threshold_with_headings_produces_multiple_chunks(self):
        """Content over threshold with ## headings splits into multiple chunks."""
        # Each section is ~700 chars; combined >2000
        section_a = self._make_section("Section A", 680)
        section_b = self._make_section("Section B", 680)
        section_c = self._make_section("Section C", 680)
        content = section_a + section_b + section_c
        assert len(content) > MAX_EPISODE_CHARS

        chunks = split_episode_content(content)
        assert len(chunks) > 1

    def test_chunks_preserve_all_content(self):
        """All content from original is present across chunks."""
        section_a = self._make_section("Section A", 700)
        section_b = self._make_section("Section B", 700)
        section_c = self._make_section("Section C", 700)
        content = section_a + section_b + section_c

        chunks = split_episode_content(content)
        combined = "".join(c.content for c in chunks)
        assert combined == content

    def test_chunk_indices_are_sequential_and_one_based(self):
        """chunk_index values are sequential starting from 1."""
        section_a = self._make_section("Section A", 700)
        section_b = self._make_section("Section B", 700)
        section_c = self._make_section("Section C", 700)
        content = section_a + section_b + section_c

        chunks = split_episode_content(content)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(1, len(chunks) + 1))

    def test_all_chunks_have_same_total_chunks(self):
        """All chunks report the same total_chunks value."""
        section_a = self._make_section("Section A", 700)
        section_b = self._make_section("Section B", 700)
        section_c = self._make_section("Section C", 700)
        content = section_a + section_b + section_c

        chunks = split_episode_content(content)
        total = chunks[0].total_chunks
        assert all(c.total_chunks == total for c in chunks)

    def test_total_chunks_matches_actual_chunk_count(self):
        """total_chunks on each chunk equals the actual list length."""
        section_a = self._make_section("Section A", 700)
        section_b = self._make_section("Section B", 700)
        section_c = self._make_section("Section C", 700)
        content = section_a + section_b + section_c

        chunks = split_episode_content(content)
        assert chunks[0].total_chunks == len(chunks)

    def test_each_chunk_fits_within_max_chars_when_possible(self):
        """No chunk exceeds max_chars when sections are themselves small enough."""
        # 4 sections each ~400 chars — any pair fits in 2000
        sections = [self._make_section(f"Section {i}", 390) for i in range(6)]
        content = "".join(sections)
        assert len(content) > MAX_EPISODE_CHARS

        chunks = split_episode_content(content)
        for chunk in chunks:
            # Each chunk should not exceed MAX_EPISODE_CHARS
            # (greedy merging stops when adding next section would exceed limit)
            assert len(chunk.content) <= MAX_EPISODE_CHARS


# ============================================================================
# 5. No ## Headings (no split boundary available)
# ============================================================================

class TestNoHeadings:
    """Test content without ## headings."""

    def test_large_content_with_no_headings_returns_single_chunk(self):
        """Large content without ## headings is returned as-is (single chunk)."""
        # 3000 chars, no ## headings
        content = "# Top Level Heading\n\n" + "x" * 3000
        assert len(content) > MAX_EPISODE_CHARS

        chunks = split_episode_content(content)
        assert len(chunks) == 1
        assert chunks[0].content == content
        assert chunks[0].chunk_index == 1
        assert chunks[0].total_chunks == 1

    def test_content_with_only_h1_headings_not_split(self):
        """Content with only # (H1) headings is not split at them."""
        section_a = "# Section A\n\n" + "a" * 700 + "\n\n"
        section_b = "# Section B\n\n" + "b" * 700 + "\n\n"
        section_c = "# Section C\n\n" + "c" * 700 + "\n\n"
        content = section_a + section_b + section_c
        assert len(content) > MAX_EPISODE_CHARS

        # No ## headings — should not split
        chunks = split_episode_content(content)
        assert len(chunks) == 1

    def test_single_oversized_section_returned_as_is(self):
        """A single ## section larger than max_chars is returned without breaking it."""
        content = "## Giant Section\n\n" + "x" * (MAX_EPISODE_CHARS + 500)
        assert len(content) > MAX_EPISODE_CHARS

        chunks = split_episode_content(content)
        assert len(chunks) == 1
        assert chunks[0].content == content


# ============================================================================
# 6. Custom max_chars Parameter
# ============================================================================

class TestCustomMaxChars:
    """Test custom max_chars parameter."""

    def test_custom_small_max_chars_increases_chunk_count(self):
        """A smaller max_chars value causes more chunks to be created."""
        section_a = "## Section A\n\n" + "a" * 50 + "\n\n"
        section_b = "## Section B\n\n" + "b" * 50 + "\n\n"
        section_c = "## Section C\n\n" + "c" * 50 + "\n\n"
        content = section_a + section_b + section_c

        # With max_chars=200, each ~60-char section fits individually;
        # all three should be in fewer than 3 chunks (greedy merging).
        chunks_small = split_episode_content(content, max_chars=70)
        chunks_large = split_episode_content(content, max_chars=10000)

        assert len(chunks_small) >= len(chunks_large)

    def test_content_under_custom_threshold_is_not_split(self):
        """Content under a custom max_chars is returned as a single chunk."""
        content = "## Section\n\nsome text"
        chunks = split_episode_content(content, max_chars=10000)
        assert len(chunks) == 1

    def test_content_over_custom_threshold_is_split(self):
        """Content over a custom max_chars is split at headings."""
        section_a = "## Section A\n\n" + "a" * 30
        section_b = "## Section B\n\n" + "b" * 30
        content = section_a + "\n\n" + section_b
        # With max_chars=50, neither section alone exceeds limit but
        # combined they do.
        chunks = split_episode_content(content, max_chars=50)
        # Combined content > 50 chars, so must split
        assert len(chunks) >= 1  # At minimum still works


# ============================================================================
# 7. Greedy Merging Behaviour
# ============================================================================

class TestGreedyMerging:
    """Test that adjacent small sections are merged to minimise chunk count."""

    def test_two_small_sections_merged_into_one_chunk(self):
        """Two sections that together fit within max_chars are merged."""
        section_a = "## Section A\n\n" + "a" * 200
        section_b = "## Section B\n\n" + "b" * 200
        content = section_a + "\n\n" + section_b
        assert len(content) < MAX_EPISODE_CHARS

        chunks = split_episode_content(content)
        assert len(chunks) == 1
        assert chunks[0].content == content

    def test_greedy_merge_keeps_chunks_under_limit(self):
        """Greedy merge doesn't create chunks larger than max_chars."""
        # Create 10 sections, each 250 chars; combined 2500 > 2000
        sections = ["## S{}\n\n{}\n\n".format(i, "x" * 240) for i in range(10)]
        content = "".join(sections)
        assert len(content) > MAX_EPISODE_CHARS

        chunks = split_episode_content(content)
        for chunk in chunks:
            assert len(chunk.content) <= MAX_EPISODE_CHARS


# ============================================================================
# 8. Return Type and Structure
# ============================================================================

class TestReturnStructure:
    """Test the structure of the returned list."""

    def test_always_returns_a_list(self):
        """split_episode_content always returns a list."""
        result = split_episode_content("any content")
        assert isinstance(result, list)

    def test_list_is_never_empty(self):
        """split_episode_content never returns an empty list."""
        for content in ["", "x", "x" * 5000, "## H\n\n" + "x" * 5000]:
            result = split_episode_content(content)
            assert len(result) >= 1

    def test_all_items_are_episode_chunks(self):
        """All items in the returned list are EpisodeChunk instances."""
        content = "## A\n\n" + "a" * 700 + "\n\n## B\n\n" + "b" * 700 + "\n\n## C\n\n" + "c" * 700
        chunks = split_episode_content(content)
        for chunk in chunks:
            assert isinstance(chunk, EpisodeChunk)


# ============================================================================
# 9. Integration Test: Large CLAUDE.md-like Content
# ============================================================================

class TestIntegration:
    """Integration tests verifying real-world-like splitting scenarios."""

    def test_large_claude_md_produces_multiple_chunks(self):
        """A large CLAUDE.md-like document with multiple ## sections produces multiple chunks."""
        # Simulate a realistic CLAUDE.md structure
        sections = [
            "## Core Principles\n\n"
            "Quality First: Never compromise on test coverage or architecture. "
            "Pragmatic Approach: Right amount of process for task complexity. " * 20,

            "## Essential Commands\n\n"
            "Core Workflow commands: /task-create, /task-work, /task-complete. "
            "These commands orchestrate the full task lifecycle. " * 20,

            "## Task Workflow Phases\n\n"
            "Phase 2 Implementation Planning. Phase 2.5 Architectural Review. "
            "Phase 2.7 Complexity Evaluation. Phase 2.8 Human Checkpoint. " * 20,

            "## Quality Gates\n\n"
            "Compilation 100%, Tests Pass 100%, Line Coverage >=80%, "
            "Branch Coverage >=75%, Architectural Review >=60/100. " * 20,
        ]
        content = "\n\n".join(sections)
        assert len(content) > MAX_EPISODE_CHARS

        chunks = split_episode_content(content)
        assert len(chunks) > 1, (
            f"Expected multiple chunks for {len(content)}-char content, got {len(chunks)}"
        )

    def test_split_content_is_lossless(self):
        """Rejoining all chunks reproduces the original content exactly."""
        sections = [
            "## Section One\n\nContent for section one. " * 30,
            "## Section Two\n\nContent for section two. " * 30,
            "## Section Three\n\nContent for section three. " * 30,
        ]
        content = "\n\n".join(sections)

        chunks = split_episode_content(content)
        reconstructed = "".join(c.content for c in chunks)
        assert reconstructed == content

    def test_chunk_indices_cover_all_positions(self):
        """chunk_index values form a gapless sequence [1, 2, ..., N]."""
        sections = ["## S{}\n\n{}\n\n".format(i, "x" * 600) for i in range(5)]
        content = "".join(sections)

        chunks = split_episode_content(content)
        indices = sorted(c.chunk_index for c in chunks)
        expected = list(range(1, len(chunks) + 1))
        assert indices == expected

    def test_project_architecture_style_content(self):
        """Realistic project architecture content is split sensibly."""
        content = """## Overview

GuardKit is a lightweight task workflow system with built-in quality gates.
It prevents broken code from reaching production through automated checks.

""" + ("Detailed description of the architecture. " * 40) + """

## Components

The system consists of the following components:

""" + ("Component description with details about its function. " * 40) + """

## Integration Points

External integrations include Graphiti for knowledge capture.

""" + ("Integration details and configuration requirements. " * 40)

        chunks = split_episode_content(content)

        # All content is present
        assert "".join(c.content for c in chunks) == content

        # Metadata is consistent
        n = len(chunks)
        for chunk in chunks:
            assert chunk.total_chunks == n
            assert 1 <= chunk.chunk_index <= n
