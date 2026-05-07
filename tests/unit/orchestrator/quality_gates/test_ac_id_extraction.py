"""Unit tests for ``CoachValidator._extract_ac_id`` (TASK-CVAC-001).

Covers extraction of acceptance-criterion IDs from criterion markdown
text in the four supported formats:

1. ``**AC-LOAD-01** — text``  (markdown bold + compound + em-dash)
2. ``**AC-001** — text``      (markdown bold + simple + em-dash)
3. ``AC-LOAD-01: text``       (compound + colon, no bold)
4. ``AC-001: text``           (simple + colon, no bold)

Plus the unlabelled control case (no AC ID present at all) and edge
cases that must NOT match (unmatched bold, prose mention without
separator, lowercase IDs).

The round-trip test (AC-CVAC-05) confirms that the extracted ID + the
returned text reconstruct the original meaning when paired with the
checkbox-stripping logic in ``_strip_criterion_prefix``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator


# ============================================================================
# AC-CVAC-01 — extraction across all four supported formats
# ============================================================================


class TestExtractAcId:
    """Test ``_extract_ac_id`` recognises all four AC ID formats."""

    def test_format_1_bold_compound_emdash(self):
        """Format 1: ``**AC-LOAD-01** — text`` (bold + compound + em-dash)."""
        text, ac_id = CoachValidator._extract_ac_id(
            "**AC-LOAD-01** — Settings class has log_level field"
        )
        assert ac_id == "AC-LOAD-01"
        assert text == "Settings class has log_level field"

    def test_format_2_bold_simple_emdash(self):
        """Format 2: ``**AC-001** — text`` (bold + simple + em-dash)."""
        text, ac_id = CoachValidator._extract_ac_id(
            "**AC-001** — Implement user authentication"
        )
        assert ac_id == "AC-001"
        assert text == "Implement user authentication"

    def test_format_3_compound_colon(self):
        """Format 3: ``AC-LOAD-01: text`` (compound + colon, no bold)."""
        text, ac_id = CoachValidator._extract_ac_id(
            "AC-LOAD-01: Settings class has log_level field"
        )
        assert ac_id == "AC-LOAD-01"
        assert text == "Settings class has log_level field"

    def test_format_4_simple_colon(self):
        """Format 4: ``AC-001: text`` (simple + colon — existing format)."""
        text, ac_id = CoachValidator._extract_ac_id(
            "AC-001: Implement user authentication"
        )
        assert ac_id == "AC-001"
        assert text == "Implement user authentication"

    def test_compound_three_segments(self):
        """Compound IDs with multiple dash-separated segments."""
        text, ac_id = CoachValidator._extract_ac_id("AC-FOO-BAR-01: text")
        assert ac_id == "AC-FOO-BAR-01"
        assert text == "text"

    def test_separator_em_dash(self):
        """Em-dash (U+2014) separator works without bold."""
        text, ac_id = CoachValidator._extract_ac_id("AC-LOAD-01 — text")
        assert ac_id == "AC-LOAD-01"
        assert text == "text"

    def test_separator_hyphen(self):
        """ASCII hyphen separator works."""
        text, ac_id = CoachValidator._extract_ac_id("AC-LOAD-01 - text")
        assert ac_id == "AC-LOAD-01"
        assert text == "text"

    def test_leading_whitespace_tolerated(self):
        """Leading whitespace before the ID is tolerated."""
        text, ac_id = CoachValidator._extract_ac_id(
            "   AC-LOAD-01: text"
        )
        assert ac_id == "AC-LOAD-01"
        assert text == "text"


# ============================================================================
# Unlabelled control + edge cases (must NOT match)
# ============================================================================


class TestExtractAcIdNoMatch:
    """Test ``_extract_ac_id`` conservatively returns ``None`` on edge cases."""

    def test_unlabelled_returns_none(self):
        """Plain text without any AC ID returns (input, None)."""
        text, ac_id = CoachValidator._extract_ac_id(
            "description text with no AC ID"
        )
        assert ac_id is None
        assert text == "description text with no AC ID"

    def test_empty_string(self):
        """Empty string returns (empty, None)."""
        text, ac_id = CoachValidator._extract_ac_id("")
        assert ac_id is None
        assert text == ""

    def test_unmatched_bold_marker(self):
        """``**AC-LOAD-01: text`` (only opening bold) — conservative no-match."""
        # Per task spec: don't silently mangle input on unmatched bold.
        text, ac_id = CoachValidator._extract_ac_id(
            "**AC-LOAD-01: text"
        )
        assert ac_id is None
        assert text == "**AC-LOAD-01: text"

    def test_prose_mention_without_separator(self):
        """``**AC-LOAD-01** is implemented`` (no separator) — no match."""
        text, ac_id = CoachValidator._extract_ac_id(
            "**AC-LOAD-01** is implemented in module X"
        )
        assert ac_id is None
        assert text == "**AC-LOAD-01** is implemented in module X"

    def test_lowercase_id_not_matched(self):
        """Lowercase ID body (``AC-load-01``) does not match — uppercase only."""
        text, ac_id = CoachValidator._extract_ac_id("AC-load-01: text")
        assert ac_id is None
        assert text == "AC-load-01: text"

    def test_id_without_segments(self):
        """``AC:`` alone (no dash-separated segments) does not match."""
        text, ac_id = CoachValidator._extract_ac_id("AC: bare prefix text")
        assert ac_id is None
        assert text == "AC: bare prefix text"

    def test_bold_simple_with_colon_separator(self):
        """``**AC-001**: text`` (bold + colon) is also recognised."""
        text, ac_id = CoachValidator._extract_ac_id("**AC-001**: text")
        assert ac_id == "AC-001"
        assert text == "text"


# ============================================================================
# AC-CVAC-05 — Round-trip extraction + matching
# ============================================================================


class TestExtractAcIdRoundTrip:
    """End-to-end round trip: extract ID, then match against a promise key."""

    @pytest.mark.parametrize(
        "criterion_text,expected_id",
        [
            ("**AC-LOAD-01** — Settings class has log_level field", "AC-LOAD-01"),
            ("**AC-001** — Implement user authentication", "AC-001"),
            ("AC-LOAD-01: Settings class has log_level field", "AC-LOAD-01"),
            ("AC-001: Implement user authentication", "AC-001"),
        ],
    )
    def test_round_trip_matches_promise_key(
        self, criterion_text: str, expected_id: str,
    ):
        """All four formats produce IDs that match Player promise keys."""
        # Simulate Player's promise: emitted with the natural label.
        promise_map = {expected_id: {"status": "complete"}}

        # Coach's extraction → use this as the promise_map lookup key.
        _, extracted_id = CoachValidator._extract_ac_id(criterion_text)
        assert extracted_id == expected_id

        # Round-trip: extracted ID is a valid promise_map key.
        assert promise_map.get(extracted_id) is not None
        assert promise_map[extracted_id]["status"] == "complete"

    def test_unlabelled_control_falls_through_to_index_id(self):
        """Unlabelled criterion → ``None`` → caller uses ``AC-{i+1:03d}``."""
        # Caller pattern: ``criterion_id = extracted_ids[i] or f"AC-{i+1:03d}"``
        _, extracted_id = CoachValidator._extract_ac_id(
            "Plain description text"
        )
        assert extracted_id is None

        # Backwards-compat: index-based fallback gives the canonical ID.
        i = 0
        criterion_id = extracted_id or f"AC-{i+1:03d}"
        assert criterion_id == "AC-001"


# ============================================================================
# Integration with _strip_criterion_prefix (existing behaviour preserved)
# ============================================================================


class TestExtractAcIdAfterStripPrefix:
    """Pre-cleaning with ``_strip_criterion_prefix`` does not mask compound IDs."""

    def test_checkbox_then_compound_id(self):
        """``- [ ] **AC-LOAD-01** — text`` → strip checkbox → extract compound."""
        # Step 1: strip checkbox prefix.
        cleaned = CoachValidator._strip_criterion_prefix(
            "- [ ] **AC-LOAD-01** — Settings class has log_level field"
        )
        # _strip_criterion_prefix does NOT touch the bold compound prefix.
        assert cleaned.startswith("**AC-LOAD-01**")

        # Step 2: extract the AC ID.
        text, ac_id = CoachValidator._extract_ac_id(cleaned)
        assert ac_id == "AC-LOAD-01"
        assert text == "Settings class has log_level field"

    def test_checkbox_then_simple_id_extracted(self):
        """``- [ ] AC-001: text`` — checkbox stripped, AC label preserved, then extracted.

        TASK-GK-CV-001: previously ``_strip_criterion_prefix`` consumed the
        ``AC-001:`` prefix, blocking ``_extract_ac_id`` from reading the
        label. After the fix, the strip helper handles only checkbox/bullet/
        numbered prefixes; ``_extract_ac_id`` correctly extracts the AC ID.
        """
        cleaned = CoachValidator._strip_criterion_prefix(
            "- [ ] AC-001: Implement user authentication"
        )
        # AC label is preserved through the strip step.
        assert cleaned == "AC-001: Implement user authentication"

        text, ac_id = CoachValidator._extract_ac_id(cleaned)
        # Simple AC ID is now extracted (not silently dropped).
        assert ac_id == "AC-001"
        assert text == "Implement user authentication"

    def test_checkbox_then_natural_label_id_extracted(self):
        """``- [ ] AC-1: text`` — natural-label (not zero-padded) is extracted.

        TASK-GK-CV-001: this is the FEAT-PEBR run-2 fingerprint. Pre-fix,
        the criterion_id would have been ``AC-001`` (zero-padded fallback)
        and Player promises with ``criterion_id="AC-1"`` would miss. Post-fix,
        the criterion_id matches the natural label exactly.
        """
        cleaned = CoachValidator._strip_criterion_prefix(
            "- [ ] AC-1: Implement user authentication"
        )
        assert cleaned == "AC-1: Implement user authentication"

        text, ac_id = CoachValidator._extract_ac_id(cleaned)
        assert ac_id == "AC-1"
        assert text == "Implement user authentication"
