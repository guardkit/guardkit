"""Unit tests for Promise-Based Completion Verification schemas.

This module tests the dataclasses and utility functions in
guardkit/orchestrator/schemas.py for the Player-Coach promise-based
verification system.

Coverage Target: >=85%
Test Count: 30+ tests
"""

import pytest

from guardkit.orchestrator.schemas import (
    CriterionStatus,
    VerificationResult,
    CompletionPromise,
    CriterionVerification,
    calculate_completion_percentage,
    format_promise_summary,
    format_verification_summary,
)


# ============================================================================
# 1. Enum Tests
# ============================================================================


class TestCriterionStatus:
    """Test CriterionStatus enum."""

    def test_complete_value(self):
        """CriterionStatus.COMPLETE has correct value."""
        assert CriterionStatus.COMPLETE.value == "complete"

    def test_incomplete_value(self):
        """CriterionStatus.INCOMPLETE has correct value."""
        assert CriterionStatus.INCOMPLETE.value == "incomplete"

    def test_is_string_enum(self):
        """CriterionStatus is a string enum."""
        assert isinstance(CriterionStatus.COMPLETE, str)
        assert CriterionStatus.COMPLETE == "complete"

    def test_all_values(self):
        """CriterionStatus has exactly 2 values."""
        values = [status.value for status in CriterionStatus]
        assert len(values) == 2
        assert "complete" in values
        assert "incomplete" in values


class TestVerificationResult:
    """Test VerificationResult enum."""

    def test_verified_value(self):
        """VerificationResult.VERIFIED has correct value."""
        assert VerificationResult.VERIFIED.value == "verified"

    def test_rejected_value(self):
        """VerificationResult.REJECTED has correct value."""
        assert VerificationResult.REJECTED.value == "rejected"

    def test_is_string_enum(self):
        """VerificationResult is a string enum."""
        assert isinstance(VerificationResult.VERIFIED, str)
        assert VerificationResult.VERIFIED == "verified"

    def test_all_values(self):
        """VerificationResult has exactly 2 values."""
        values = [result.value for result in VerificationResult]
        assert len(values) == 2
        assert "verified" in values
        assert "rejected" in values


# ============================================================================
# 2. CompletionPromise Tests
# ============================================================================


class TestCompletionPromise:
    """Test CompletionPromise dataclass."""

    @pytest.fixture
    def sample_promise(self):
        """Create a sample CompletionPromise for testing."""
        return CompletionPromise(
            criterion_id="AC-001",
            criterion_text="OAuth2 authentication flow works correctly",
            status=CriterionStatus.COMPLETE,
            evidence="Implemented OAuth2 flow in src/auth/oauth.py with PKCE support",
            test_file="tests/test_oauth.py",
            implementation_files=["src/auth/oauth.py", "src/auth/tokens.py"],
        )

    def test_creation_with_required_fields(self):
        """CompletionPromise can be created with required fields."""
        promise = CompletionPromise(
            criterion_id="AC-001",
            criterion_text="Test criterion",
            status=CriterionStatus.COMPLETE,
            evidence="Test evidence",
        )

        assert promise.criterion_id == "AC-001"
        assert promise.criterion_text == "Test criterion"
        assert promise.status == CriterionStatus.COMPLETE
        assert promise.evidence == "Test evidence"
        assert promise.test_file is None
        assert promise.implementation_files == []

    def test_creation_with_all_fields(self, sample_promise):
        """CompletionPromise can be created with all fields."""
        assert sample_promise.criterion_id == "AC-001"
        assert sample_promise.criterion_text == "OAuth2 authentication flow works correctly"
        assert sample_promise.status == CriterionStatus.COMPLETE
        assert sample_promise.evidence == "Implemented OAuth2 flow in src/auth/oauth.py with PKCE support"
        assert sample_promise.test_file == "tests/test_oauth.py"
        assert sample_promise.implementation_files == ["src/auth/oauth.py", "src/auth/tokens.py"]

    def test_to_dict(self, sample_promise):
        """CompletionPromise.to_dict() returns correct dictionary."""
        result = sample_promise.to_dict()

        assert result["criterion_id"] == "AC-001"
        assert result["criterion_text"] == "OAuth2 authentication flow works correctly"
        assert result["status"] == "complete"  # enum value, not enum
        assert result["evidence"] == "Implemented OAuth2 flow in src/auth/oauth.py with PKCE support"
        assert result["test_file"] == "tests/test_oauth.py"
        assert result["implementation_files"] == ["src/auth/oauth.py", "src/auth/tokens.py"]

    def test_to_dict_with_none_test_file(self):
        """CompletionPromise.to_dict() handles None test_file."""
        promise = CompletionPromise(
            criterion_id="AC-002",
            criterion_text="Simple criterion",
            status=CriterionStatus.INCOMPLETE,
            evidence="Work in progress",
        )

        result = promise.to_dict()

        assert result["test_file"] is None
        assert result["implementation_files"] == []

    def test_from_dict_complete(self):
        """CompletionPromise.from_dict() creates instance from complete dict."""
        data = {
            "criterion_id": "AC-001",
            "criterion_text": "Token refresh handles expiry",
            "status": "complete",
            "evidence": "Added 5-minute buffer",
            "test_file": "tests/test_refresh.py",
            "implementation_files": ["src/tokens.py"],
        }

        promise = CompletionPromise.from_dict(data)

        assert promise.criterion_id == "AC-001"
        assert promise.criterion_text == "Token refresh handles expiry"
        assert promise.status == CriterionStatus.COMPLETE
        assert promise.evidence == "Added 5-minute buffer"
        assert promise.test_file == "tests/test_refresh.py"
        assert promise.implementation_files == ["src/tokens.py"]

    def test_from_dict_minimal(self):
        """CompletionPromise.from_dict() handles minimal dict with defaults."""
        data = {
            "criterion_id": "AC-003",
            "criterion_text": "Minimal criterion",
            "status": "incomplete",
            "evidence": "Not started",
        }

        promise = CompletionPromise.from_dict(data)

        assert promise.criterion_id == "AC-003"
        assert promise.status == CriterionStatus.INCOMPLETE
        assert promise.test_file is None
        assert promise.implementation_files == []

    def test_from_dict_with_missing_fields(self):
        """CompletionPromise.from_dict() uses defaults for missing fields."""
        data = {}

        promise = CompletionPromise.from_dict(data)

        assert promise.criterion_id == ""
        assert promise.criterion_text == ""
        assert promise.status == CriterionStatus.INCOMPLETE  # default
        assert promise.evidence == ""
        assert promise.test_file is None
        assert promise.implementation_files == []

    def test_roundtrip(self, sample_promise):
        """CompletionPromise round-trips through to_dict/from_dict."""
        data = sample_promise.to_dict()
        restored = CompletionPromise.from_dict(data)

        assert restored.criterion_id == sample_promise.criterion_id
        assert restored.criterion_text == sample_promise.criterion_text
        assert restored.status == sample_promise.status
        assert restored.evidence == sample_promise.evidence
        assert restored.test_file == sample_promise.test_file
        assert restored.implementation_files == sample_promise.implementation_files


# ============================================================================
# 3. CriterionVerification Tests
# ============================================================================


class TestCriterionVerification:
    """Test CriterionVerification dataclass."""

    @pytest.fixture
    def sample_verification(self):
        """Create a sample CriterionVerification for testing."""
        return CriterionVerification(
            criterion_id="AC-001",
            result=VerificationResult.VERIFIED,
            notes="Tests pass, implementation matches requirements",
        )

    def test_creation(self, sample_verification):
        """CriterionVerification can be created with all fields."""
        assert sample_verification.criterion_id == "AC-001"
        assert sample_verification.result == VerificationResult.VERIFIED
        assert sample_verification.notes == "Tests pass, implementation matches requirements"

    def test_to_dict_verified(self, sample_verification):
        """CriterionVerification.to_dict() returns correct dict for VERIFIED."""
        result = sample_verification.to_dict()

        assert result["criterion_id"] == "AC-001"
        assert result["result"] == "verified"  # enum value
        assert result["notes"] == "Tests pass, implementation matches requirements"

    def test_to_dict_rejected(self):
        """CriterionVerification.to_dict() returns correct dict for REJECTED."""
        verification = CriterionVerification(
            criterion_id="AC-002",
            result=VerificationResult.REJECTED,
            notes="Missing edge case handling",
        )

        result = verification.to_dict()

        assert result["criterion_id"] == "AC-002"
        assert result["result"] == "rejected"
        assert result["notes"] == "Missing edge case handling"

    def test_from_dict_verified(self):
        """CriterionVerification.from_dict() creates VERIFIED instance."""
        data = {
            "criterion_id": "AC-001",
            "result": "verified",
            "notes": "All tests pass",
        }

        verification = CriterionVerification.from_dict(data)

        assert verification.criterion_id == "AC-001"
        assert verification.result == VerificationResult.VERIFIED
        assert verification.notes == "All tests pass"

    def test_from_dict_rejected(self):
        """CriterionVerification.from_dict() creates REJECTED instance."""
        data = {
            "criterion_id": "AC-002",
            "result": "rejected",
            "notes": "Missing implementation",
        }

        verification = CriterionVerification.from_dict(data)

        assert verification.criterion_id == "AC-002"
        assert verification.result == VerificationResult.REJECTED
        assert verification.notes == "Missing implementation"

    def test_from_dict_with_missing_fields(self):
        """CriterionVerification.from_dict() uses defaults for missing fields."""
        data = {}

        verification = CriterionVerification.from_dict(data)

        assert verification.criterion_id == ""
        assert verification.result == VerificationResult.REJECTED  # default
        assert verification.notes == ""

    def test_roundtrip(self, sample_verification):
        """CriterionVerification round-trips through to_dict/from_dict."""
        data = sample_verification.to_dict()
        restored = CriterionVerification.from_dict(data)

        assert restored.criterion_id == sample_verification.criterion_id
        assert restored.result == sample_verification.result
        assert restored.notes == sample_verification.notes


# ============================================================================
# 4. calculate_completion_percentage Tests
# ============================================================================


class TestCalculateCompletionPercentage:
    """Test calculate_completion_percentage utility function."""

    def test_empty_promises(self):
        """Returns 0.0 for empty promises list."""
        result = calculate_completion_percentage([], [])
        assert result == 0.0

    def test_no_verifications(self):
        """Returns 0.0 when no verifications exist."""
        promises = [
            CompletionPromise("AC-001", "Criterion 1", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-002", "Criterion 2", CriterionStatus.COMPLETE, "Done"),
        ]

        result = calculate_completion_percentage(promises, [])

        assert result == 0.0

    def test_all_verified(self):
        """Returns 100.0 when all promises are verified."""
        promises = [
            CompletionPromise("AC-001", "Criterion 1", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-002", "Criterion 2", CriterionStatus.COMPLETE, "Done"),
        ]
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
            CriterionVerification("AC-002", VerificationResult.VERIFIED, "Good"),
        ]

        result = calculate_completion_percentage(promises, verifications)

        assert result == 100.0

    def test_half_verified(self):
        """Returns 50.0 when half are verified."""
        promises = [
            CompletionPromise("AC-001", "Criterion 1", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-002", "Criterion 2", CriterionStatus.COMPLETE, "Done"),
        ]
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
        ]

        result = calculate_completion_percentage(promises, verifications)

        assert result == 50.0

    def test_rejected_not_counted(self):
        """Rejected verifications are not counted as complete."""
        promises = [
            CompletionPromise("AC-001", "Criterion 1", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-002", "Criterion 2", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-003", "Criterion 3", CriterionStatus.COMPLETE, "Done"),
        ]
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
            CriterionVerification("AC-002", VerificationResult.REJECTED, "Missing feature"),
            CriterionVerification("AC-003", VerificationResult.VERIFIED, "Good"),
        ]

        result = calculate_completion_percentage(promises, verifications)

        # 2 verified out of 3
        assert abs(result - 66.67) < 0.1

    def test_one_of_three(self):
        """Returns ~33.3 when one of three is verified."""
        promises = [
            CompletionPromise("AC-001", "Criterion 1", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-002", "Criterion 2", CriterionStatus.INCOMPLETE, "WIP"),
            CompletionPromise("AC-003", "Criterion 3", CriterionStatus.INCOMPLETE, "WIP"),
        ]
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
        ]

        result = calculate_completion_percentage(promises, verifications)

        assert abs(result - 33.33) < 0.1

    def test_extra_verifications_ignored(self):
        """Extra verifications not matching promises are ignored."""
        promises = [
            CompletionPromise("AC-001", "Criterion 1", CriterionStatus.COMPLETE, "Done"),
        ]
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
            CriterionVerification("AC-999", VerificationResult.VERIFIED, "Unknown"),
        ]

        result = calculate_completion_percentage(promises, verifications)

        assert result == 100.0


# ============================================================================
# 5. format_promise_summary Tests
# ============================================================================


class TestFormatPromiseSummary:
    """Test format_promise_summary utility function."""

    def test_empty_list(self):
        """Returns 'No completion promises' for empty list."""
        result = format_promise_summary([])
        assert result == "No completion promises"

    def test_single_complete(self):
        """Formats single complete promise correctly."""
        promises = [
            CompletionPromise("AC-001", "OAuth flow", CriterionStatus.COMPLETE, "Done"),
        ]

        result = format_promise_summary(promises)

        assert "Completion Promises:" in result
        assert "[COMPLETE] AC-001: OAuth flow" in result

    def test_single_incomplete(self):
        """Formats single incomplete promise correctly."""
        promises = [
            CompletionPromise("AC-002", "Token refresh", CriterionStatus.INCOMPLETE, "WIP"),
        ]

        result = format_promise_summary(promises)

        assert "[INCOMPLETE] AC-002: Token refresh" in result

    def test_mixed_statuses(self):
        """Formats mixed complete/incomplete promises."""
        promises = [
            CompletionPromise("AC-001", "OAuth flow", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-002", "Token refresh", CriterionStatus.INCOMPLETE, "WIP"),
        ]

        result = format_promise_summary(promises)

        assert "[COMPLETE] AC-001: OAuth flow" in result
        assert "[INCOMPLETE] AC-002: Token refresh" in result

    def test_truncates_long_criterion_text(self):
        """Truncates criterion text longer than 50 characters."""
        long_text = "This is a very long acceptance criterion that exceeds fifty characters"
        promises = [
            CompletionPromise("AC-001", long_text, CriterionStatus.COMPLETE, "Done"),
        ]

        result = format_promise_summary(promises)

        assert "..." in result
        # Should truncate at 50 chars + ...
        assert long_text[:50] in result

    def test_preserves_order(self):
        """Preserves order of promises in output."""
        promises = [
            CompletionPromise("AC-003", "Third", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-001", "First", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-002", "Second", CriterionStatus.COMPLETE, "Done"),
        ]

        result = format_promise_summary(promises)
        lines = result.split("\n")

        # Header is first, then promises in order
        assert "AC-003: Third" in lines[1]
        assert "AC-001: First" in lines[2]
        assert "AC-002: Second" in lines[3]


# ============================================================================
# 6. format_verification_summary Tests
# ============================================================================


class TestFormatVerificationSummary:
    """Test format_verification_summary utility function."""

    def test_empty_list(self):
        """Returns 'No verifications' for empty list."""
        result = format_verification_summary([])
        assert result == "No verifications"

    def test_single_verified(self):
        """Formats single verified result correctly."""
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
        ]

        result = format_verification_summary(verifications)

        assert "Verification Results:" in result
        assert "[VERIFIED] AC-001: Good" in result

    def test_single_rejected(self):
        """Formats single rejected result correctly."""
        verifications = [
            CriterionVerification("AC-002", VerificationResult.REJECTED, "Missing tests"),
        ]

        result = format_verification_summary(verifications)

        assert "[REJECTED] AC-002: Missing tests" in result

    def test_mixed_results(self):
        """Formats mixed verified/rejected results."""
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
            CriterionVerification("AC-002", VerificationResult.REJECTED, "Missing edge case"),
        ]

        result = format_verification_summary(verifications)

        assert "[VERIFIED] AC-001: Good" in result
        assert "[REJECTED] AC-002: Missing edge case" in result

    def test_truncates_long_notes(self):
        """Truncates notes longer than 50 characters."""
        long_notes = "This is a very long verification note that exceeds the fifty character limit"
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, long_notes),
        ]

        result = format_verification_summary(verifications)

        assert "..." in result
        assert long_notes[:50] in result

    def test_preserves_order(self):
        """Preserves order of verifications in output."""
        verifications = [
            CriterionVerification("AC-003", VerificationResult.VERIFIED, "Third"),
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "First"),
            CriterionVerification("AC-002", VerificationResult.REJECTED, "Second"),
        ]

        result = format_verification_summary(verifications)
        lines = result.split("\n")

        # Header is first, then verifications in order
        assert "AC-003: Third" in lines[1]
        assert "AC-001: First" in lines[2]
        assert "AC-002: Second" in lines[3]


# ============================================================================
# 7. Edge Case and Integration Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_promise_with_empty_implementation_files(self):
        """CompletionPromise handles empty implementation_files list."""
        promise = CompletionPromise(
            criterion_id="AC-001",
            criterion_text="Test",
            status=CriterionStatus.COMPLETE,
            evidence="Evidence",
            implementation_files=[],
        )

        assert promise.implementation_files == []
        data = promise.to_dict()
        assert data["implementation_files"] == []

    def test_verification_with_empty_notes(self):
        """CriterionVerification handles empty notes."""
        verification = CriterionVerification(
            criterion_id="AC-001",
            result=VerificationResult.VERIFIED,
            notes="",
        )

        assert verification.notes == ""
        data = verification.to_dict()
        assert data["notes"] == ""

    def test_calculate_percentage_with_single_item(self):
        """calculate_completion_percentage works with single promise."""
        promises = [
            CompletionPromise("AC-001", "Only one", CriterionStatus.COMPLETE, "Done"),
        ]
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
        ]

        result = calculate_completion_percentage(promises, verifications)
        assert result == 100.0

    def test_all_rejected_is_zero_percent(self):
        """All rejected verifications result in 0% completion."""
        promises = [
            CompletionPromise("AC-001", "First", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-002", "Second", CriterionStatus.COMPLETE, "Done"),
        ]
        verifications = [
            CriterionVerification("AC-001", VerificationResult.REJECTED, "Failed"),
            CriterionVerification("AC-002", VerificationResult.REJECTED, "Failed"),
        ]

        result = calculate_completion_percentage(promises, verifications)
        assert result == 0.0

    def test_format_summary_special_characters(self):
        """Format functions handle special characters in text."""
        promises = [
            CompletionPromise(
                "AC-001",
                "Handle special chars: <>&\"'",
                CriterionStatus.COMPLETE,
                "Done",
            ),
        ]

        result = format_promise_summary(promises)

        assert "<>&\"'" in result

    def test_verification_id_matching_is_exact(self):
        """Verification matching is exact (AC-001 != AC-0011)."""
        promises = [
            CompletionPromise("AC-001", "First", CriterionStatus.COMPLETE, "Done"),
            CompletionPromise("AC-0011", "Second", CriterionStatus.COMPLETE, "Done"),
        ]
        verifications = [
            CriterionVerification("AC-001", VerificationResult.VERIFIED, "Good"),
        ]

        result = calculate_completion_percentage(promises, verifications)

        # Only AC-001 matches, not AC-0011
        assert result == 50.0
