"""
Test suite for Backend-Aware Acceptance Criteria Validator.

Tests cover:
- BackendKind enum validation
- Backend detection from timeout multiplier
- AC validation for cloud backends (no warnings)
- AC validation for vLLM backends (pattern matching)
- Pattern matching case-insensitivity
- Relaxed alternative suggestions
- Format report output
- Edge cases (empty criteria, mixed lists, unknown backend)

Coverage Target: >=85%
"""

import pytest

from guardkit.validation.ac_validator import (
    ACValidationResult,
    ACWarning,
    BackendKind,
    InfeasiblePattern,
    VLLM_INFEASIBLE_PATTERNS,
    _match_criterion,
    detect_backend,
    format_validation_report,
    validate_acceptance_criteria,
)


# ============================================================================
# 1. BackendKind Enum Tests
# ============================================================================


class TestBackendKindEnum:
    """Test BackendKind enum has correct values."""

    def test_cloud_value(self):
        assert BackendKind.CLOUD.value == "cloud"

    def test_local_vllm_value(self):
        assert BackendKind.LOCAL_VLLM.value == "local_vllm"

    def test_unknown_value(self):
        assert BackendKind.UNKNOWN.value == "unknown"

    def test_enum_count(self):
        assert len(BackendKind) == 3


# ============================================================================
# 2. Backend Detection Tests
# ============================================================================


class TestDetectBackend:
    """Test backend detection from timeout multiplier."""

    def test_cloud_default(self, monkeypatch):
        """Default (no env vars) returns CLOUD."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        result = detect_backend()
        assert result == BackendKind.CLOUD

    def test_local_vllm_from_base_url(self, monkeypatch):
        """localhost base URL returns LOCAL_VLLM."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000/v1")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        result = detect_backend()
        assert result == BackendKind.LOCAL_VLLM

    def test_local_vllm_from_127(self, monkeypatch):
        """127.0.0.1 base URL returns LOCAL_VLLM."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:8000/v1")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        result = detect_backend()
        assert result == BackendKind.LOCAL_VLLM

    def test_cloud_from_explicit_multiplier(self, monkeypatch):
        """Explicit multiplier 1.0 returns CLOUD."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.setenv("GUARDKIT_TIMEOUT_MULTIPLIER", "1.0")
        result = detect_backend()
        assert result == BackendKind.CLOUD

    def test_local_vllm_from_explicit_multiplier(self, monkeypatch):
        """Explicit multiplier 4.0 returns LOCAL_VLLM."""
        monkeypatch.setenv("GUARDKIT_TIMEOUT_MULTIPLIER", "4.0")
        result = detect_backend()
        assert result == BackendKind.LOCAL_VLLM

    def test_override_multiplier(self):
        """Direct multiplier override bypasses env detection."""
        assert detect_backend(timeout_multiplier=1.0) == BackendKind.CLOUD
        assert detect_backend(timeout_multiplier=4.0) == BackendKind.LOCAL_VLLM

    def test_threshold_boundary_below(self):
        """Multiplier 1.9 is CLOUD (below 2.0 threshold)."""
        assert detect_backend(timeout_multiplier=1.9) == BackendKind.CLOUD

    def test_threshold_boundary_at(self):
        """Multiplier 2.0 is LOCAL_VLLM (at threshold)."""
        assert detect_backend(timeout_multiplier=2.0) == BackendKind.LOCAL_VLLM

    def test_threshold_boundary_above(self):
        """Multiplier 2.1 is LOCAL_VLLM (above threshold)."""
        assert detect_backend(timeout_multiplier=2.1) == BackendKind.LOCAL_VLLM

    def test_invalid_multiplier_env_falls_back_to_url_detection(self, monkeypatch):
        """Non-numeric GUARDKIT_TIMEOUT_MULTIPLIER falls back to URL detection."""
        monkeypatch.setenv("GUARDKIT_TIMEOUT_MULTIPLIER", "not-a-number")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        result = detect_backend()
        assert result == BackendKind.CLOUD


# ============================================================================
# 3. Pattern Matching Tests
# ============================================================================


class TestMatchCriterion:
    """Test internal pattern matching logic."""

    def test_no_match_returns_empty_list(self):
        """Criterion with no matching pattern returns empty list."""
        result = _match_criterion("Tests pass at 80% coverage", VLLM_INFEASIBLE_PATTERNS)
        assert result == []

    def test_mypy_strict_match(self):
        """'mypy --strict' keyword matches."""
        result = _match_criterion(
            "All code passes mypy --strict with zero errors",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "mypy_strict"

    def test_zero_any_types_match(self):
        """'zero Any types' keyword matches."""
        result = _match_criterion(
            "Codebase has zero Any types in public API",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "mypy_strict"

    def test_sub_second_latency_match(self):
        """'<1s' keyword matches."""
        result = _match_criterion(
            "API response time <1s for all endpoints",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "sub_second_latency"

    def test_cloud_only_match(self):
        """'claude.ai' keyword matches."""
        result = _match_criterion(
            "Works with claude.ai API",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "cloud_only_feature"

    def test_concurrent_requests_match(self):
        """'1000 concurrent' keyword matches."""
        result = _match_criterion(
            "Handles 1000 concurrent users",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "concurrent_requests"

    def test_100_percent_coverage_match(self):
        """'100% coverage' keyword matches."""
        result = _match_criterion(
            "Must achieve 100% coverage on all modules",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "100_percent_coverage"

    def test_case_insensitive_matching(self):
        """Pattern matching is case-insensitive."""
        result = _match_criterion(
            "Code passes MYPY --STRICT checks",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "mypy_strict"

    def test_partial_match_in_longer_text(self):
        """Keywords match when embedded in longer text."""
        result = _match_criterion(
            "Ensure response latency is under 500ms for the health endpoint",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "sub_second_latency"

    def test_tokens_per_second_match(self):
        """'tokens per second' matches streaming pattern."""
        result = _match_criterion(
            "Achieves 50 tokens per second generation speed",
            VLLM_INFEASIBLE_PATTERNS,
        )
        assert len(result) == 1
        assert result[0].key == "streaming_token_rate"

    def test_multi_match_returns_all_patterns(self):
        """Criterion matching multiple patterns returns all of them."""
        result = _match_criterion(
            "Uses claude.ai API with response time <1s",
            VLLM_INFEASIBLE_PATTERNS,
        )
        keys = {p.key for p in result}
        assert "cloud_only_feature" in keys
        assert "sub_second_latency" in keys
        assert len(result) >= 2


# ============================================================================
# 4. Cloud Backend Validation Tests
# ============================================================================


class TestValidateCloudBackend:
    """Test that cloud backend returns no warnings for any criteria."""

    def test_cloud_no_warnings_for_strict_typing(self):
        """Cloud backend allows mypy --strict."""
        result = validate_acceptance_criteria(
            ["All code passes mypy --strict"],
            backend=BackendKind.CLOUD,
        )
        assert not result.has_warnings
        assert result.backend == BackendKind.CLOUD

    def test_cloud_no_warnings_for_latency(self):
        """Cloud backend allows sub-second latency."""
        result = validate_acceptance_criteria(
            ["Response time <1s"],
            backend=BackendKind.CLOUD,
        )
        assert not result.has_warnings

    def test_cloud_empty_criteria(self):
        """Cloud backend with empty criteria returns no warnings."""
        result = validate_acceptance_criteria([], backend=BackendKind.CLOUD)
        assert not result.has_warnings
        assert result.flagged_count == 0


# ============================================================================
# 5. vLLM Backend Validation Tests
# ============================================================================


class TestValidateVllmBackend:
    """Test that vLLM backend flags infeasible criteria."""

    def test_vllm_flags_mypy_strict(self):
        """vLLM backend flags mypy --strict."""
        result = validate_acceptance_criteria(
            ["All code passes mypy --strict with zero errors"],
            backend=BackendKind.LOCAL_VLLM,
        )
        assert result.has_warnings
        assert result.flagged_count == 1
        assert result.warnings[0].matched_pattern == "mypy_strict"

    def test_vllm_flags_multiple_criteria(self):
        """vLLM backend flags multiple infeasible criteria."""
        result = validate_acceptance_criteria(
            [
                "All code passes mypy --strict",
                "Response time <1s",
                "Tests pass at 80% coverage",  # This is fine
            ],
            backend=BackendKind.LOCAL_VLLM,
        )
        assert result.flagged_count == 2
        patterns = {w.matched_pattern for w in result.warnings}
        assert patterns == {"mypy_strict", "sub_second_latency"}

    def test_vllm_clean_criteria_no_warnings(self):
        """vLLM backend with clean criteria returns no warnings."""
        result = validate_acceptance_criteria(
            [
                "Tests pass at 80% coverage",
                "Code follows SOLID principles",
                "All endpoints return proper error codes",
            ],
            backend=BackendKind.LOCAL_VLLM,
        )
        assert not result.has_warnings

    def test_vllm_empty_criteria(self):
        """vLLM backend with empty criteria returns no warnings."""
        result = validate_acceptance_criteria([], backend=BackendKind.LOCAL_VLLM)
        assert not result.has_warnings

    def test_vllm_whitespace_criteria_ignored(self):
        """Whitespace-only criteria are skipped."""
        result = validate_acceptance_criteria(
            ["", "  ", "Tests pass at 80% coverage"],
            backend=BackendKind.LOCAL_VLLM,
        )
        assert not result.has_warnings

    def test_vllm_warning_has_suggestion(self):
        """Each warning includes a suggested alternative."""
        result = validate_acceptance_criteria(
            ["All code passes mypy --strict"],
            backend=BackendKind.LOCAL_VLLM,
        )
        assert result.warnings[0].suggested_alternative
        assert "disallow-untyped-defs" in result.warnings[0].suggested_alternative

    def test_vllm_warning_has_feasibility_score(self):
        """Each warning has a feasibility score."""
        result = validate_acceptance_criteria(
            ["Response time <1s"],
            backend=BackendKind.LOCAL_VLLM,
        )
        assert result.warnings[0].feasibility_score == 2

    def test_vllm_preserves_original_criterion(self):
        """Warning preserves the original criterion text."""
        original = "Must achieve 100% test coverage on all production code"
        result = validate_acceptance_criteria(
            [original],
            backend=BackendKind.LOCAL_VLLM,
        )
        assert result.warnings[0].criterion == original

    def test_vllm_multi_match_single_criterion(self):
        """Single criterion matching multiple patterns produces multiple warnings."""
        result = validate_acceptance_criteria(
            ["Uses claude.ai API with response time <1s"],
            backend=BackendKind.LOCAL_VLLM,
        )
        assert result.flagged_count >= 2
        patterns = {w.matched_pattern for w in result.warnings}
        assert "cloud_only_feature" in patterns
        assert "sub_second_latency" in patterns


# ============================================================================
# 6. Unknown Backend Tests
# ============================================================================


class TestValidateUnknownBackend:
    """Test that UNKNOWN backend gets conservative (vLLM-like) treatment."""

    def test_unknown_flags_infeasible_criteria(self):
        """UNKNOWN backend flags criteria like vLLM does."""
        result = validate_acceptance_criteria(
            ["All code passes mypy --strict"],
            backend=BackendKind.UNKNOWN,
        )
        assert result.has_warnings
        assert result.warnings[0].matched_pattern == "mypy_strict"

    def test_unknown_backend_value_in_result(self):
        """Result correctly reports UNKNOWN backend."""
        result = validate_acceptance_criteria(
            ["Tests pass"],
            backend=BackendKind.UNKNOWN,
        )
        assert result.backend == BackendKind.UNKNOWN


# ============================================================================
# 7. Auto-Detection Integration Tests
# ============================================================================


class TestAutoDetection:
    """Test validate_acceptance_criteria with auto-detected backend."""

    def test_auto_detect_cloud(self, monkeypatch):
        """Auto-detection with cloud env returns no warnings."""
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        result = validate_acceptance_criteria(
            ["All code passes mypy --strict"],
        )
        assert result.backend == BackendKind.CLOUD
        assert not result.has_warnings

    def test_auto_detect_vllm(self, monkeypatch):
        """Auto-detection with vLLM env flags infeasible criteria."""
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://localhost:8000/v1")
        monkeypatch.delenv("GUARDKIT_TIMEOUT_MULTIPLIER", raising=False)
        result = validate_acceptance_criteria(
            ["All code passes mypy --strict"],
        )
        assert result.backend == BackendKind.LOCAL_VLLM
        assert result.has_warnings


# ============================================================================
# 8. Format Report Tests
# ============================================================================


class TestFormatValidationReport:
    """Test human-readable report formatting."""

    def test_no_warnings_returns_empty_string(self):
        """Report is empty when no warnings exist."""
        result = ACValidationResult(backend=BackendKind.CLOUD)
        report = format_validation_report(result)
        assert report == ""

    def test_report_contains_backend_type(self):
        """Report includes the backend type."""
        result = ACValidationResult(
            backend=BackendKind.LOCAL_VLLM,
            warnings=[
                ACWarning(
                    criterion="mypy --strict",
                    matched_pattern="mypy_strict",
                    reason="Not achievable on vLLM",
                    suggested_alternative="Use --disallow-untyped-defs",
                    feasibility_score=2,
                ),
            ],
        )
        report = format_validation_report(result)
        assert "local_vllm" in report

    def test_report_contains_criterion_text(self):
        """Report includes the original criterion text."""
        result = ACValidationResult(
            backend=BackendKind.LOCAL_VLLM,
            warnings=[
                ACWarning(
                    criterion="All code passes mypy --strict",
                    matched_pattern="mypy_strict",
                    reason="Not achievable",
                    suggested_alternative="Use relaxed typing",
                    feasibility_score=2,
                ),
            ],
        )
        report = format_validation_report(result)
        assert "All code passes mypy --strict" in report

    def test_report_contains_suggestion(self):
        """Report includes the suggested alternative."""
        result = ACValidationResult(
            backend=BackendKind.LOCAL_VLLM,
            warnings=[
                ACWarning(
                    criterion="Response time <1s",
                    matched_pattern="sub_second_latency",
                    reason="vLLM is slower",
                    suggested_alternative="Remove hard latency bound",
                    feasibility_score=2,
                ),
            ],
        )
        report = format_validation_report(result)
        assert "Remove hard latency bound" in report

    def test_report_contains_advisory_note(self):
        """Report includes advisory (non-blocking) note."""
        result = ACValidationResult(
            backend=BackendKind.LOCAL_VLLM,
            warnings=[
                ACWarning(
                    criterion="test",
                    matched_pattern="test",
                    reason="test",
                    suggested_alternative="test",
                    feasibility_score=2,
                ),
            ],
        )
        report = format_validation_report(result)
        assert "advisory" in report.lower()

    def test_report_contains_warning_count(self):
        """Report header includes the count of warnings."""
        result = ACValidationResult(
            backend=BackendKind.LOCAL_VLLM,
            warnings=[
                ACWarning(
                    criterion="criterion 1",
                    matched_pattern="p1",
                    reason="r1",
                    suggested_alternative="s1",
                    feasibility_score=2,
                ),
                ACWarning(
                    criterion="criterion 2",
                    matched_pattern="p2",
                    reason="r2",
                    suggested_alternative="s2",
                    feasibility_score=2,
                ),
            ],
        )
        report = format_validation_report(result)
        assert "2 issue(s)" in report

    def test_report_numbers_warnings(self):
        """Report numbers each warning sequentially."""
        result = ACValidationResult(
            backend=BackendKind.LOCAL_VLLM,
            warnings=[
                ACWarning(
                    criterion="c1", matched_pattern="p1",
                    reason="r1", suggested_alternative="s1",
                    feasibility_score=2,
                ),
                ACWarning(
                    criterion="c2", matched_pattern="p2",
                    reason="r2", suggested_alternative="s2",
                    feasibility_score=2,
                ),
            ],
        )
        report = format_validation_report(result)
        assert "1." in report
        assert "2." in report


# ============================================================================
# 9. ACValidationResult Dataclass Tests
# ============================================================================


class TestACValidationResult:
    """Test ACValidationResult dataclass properties."""

    def test_empty_result_has_no_warnings(self):
        result = ACValidationResult(backend=BackendKind.CLOUD)
        assert not result.has_warnings
        assert result.flagged_count == 0

    def test_result_with_warnings(self):
        result = ACValidationResult(
            backend=BackendKind.LOCAL_VLLM,
            warnings=[
                ACWarning(
                    criterion="test",
                    matched_pattern="test",
                    reason="test",
                    suggested_alternative="test",
                    feasibility_score=2,
                ),
            ],
        )
        assert result.has_warnings
        assert result.flagged_count == 1


# ============================================================================
# 10. InfeasiblePattern Data Tests
# ============================================================================


class TestInfeasiblePatterns:
    """Test the VLLM_INFEASIBLE_PATTERNS data constant."""

    def test_patterns_not_empty(self):
        """At least one pattern is defined."""
        assert len(VLLM_INFEASIBLE_PATTERNS) > 0

    def test_all_patterns_have_required_fields(self):
        """Each pattern has key, keywords, reason, and suggested_alternative."""
        for pattern in VLLM_INFEASIBLE_PATTERNS:
            assert pattern.key, f"Pattern missing key"
            assert len(pattern.keywords) > 0, f"Pattern {pattern.key} has no keywords"
            assert pattern.reason, f"Pattern {pattern.key} missing reason"
            assert pattern.suggested_alternative, (
                f"Pattern {pattern.key} missing suggested_alternative"
            )

    def test_pattern_keys_are_unique(self):
        """Each pattern has a unique key."""
        keys = [p.key for p in VLLM_INFEASIBLE_PATTERNS]
        assert len(keys) == len(set(keys)), "Duplicate pattern keys found"

    def test_mypy_strict_pattern_exists(self):
        """The mypy_strict pattern exists (core use case from TASK-REV-5E1F)."""
        keys = {p.key for p in VLLM_INFEASIBLE_PATTERNS}
        assert "mypy_strict" in keys
