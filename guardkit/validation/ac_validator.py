"""
Backend-Aware Acceptance Criteria Validator for GuardKit.

Detects and flags infeasible acceptance criteria based on the target backend
(vLLM local vs cloud). Provides pre-flight validation for the /feature-plan
command to prevent generating unachievable criteria.

Coverage Target: >=85%
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from guardkit.orchestrator.agent_invoker import detect_timeout_multiplier


class BackendKind(Enum):
    """Target inference backend type."""

    CLOUD = "cloud"
    LOCAL_VLLM = "local_vllm"
    UNKNOWN = "unknown"


@dataclass
class InfeasiblePattern:
    """A pattern that is known to be infeasible on a specific backend."""

    key: str
    keywords: list[str]
    reason: str
    suggested_alternative: str


@dataclass
class ACWarning:
    """A single flagged acceptance criterion with a relaxed alternative."""

    criterion: str
    matched_pattern: str
    reason: str
    suggested_alternative: str
    feasibility_score: int  # 1-10, lower = less feasible


@dataclass
class ACValidationResult:
    """Outcome of pre-flight AC validation."""

    backend: BackendKind
    warnings: list[ACWarning] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        """Return True if any criteria were flagged."""
        return len(self.warnings) > 0

    @property
    def flagged_count(self) -> int:
        """Return the number of flagged criteria."""
        return len(self.warnings)


# ---------------------------------------------------------------------------
# Infeasible pattern definitions (data, not logic)
# ---------------------------------------------------------------------------

VLLM_INFEASIBLE_PATTERNS: list[InfeasiblePattern] = [
    InfeasiblePattern(
        key="mypy_strict",
        keywords=["mypy --strict", "mypy strict", "zero any types", "zero Any types",
                  "no Any types", "strict type checking"],
        reason=(
            "Local vLLM inference produces less precise code than cloud models. "
            "mypy --strict with zero Any types is not reliably achievable."
        ),
        suggested_alternative=(
            "Use 'mypy --disallow-untyped-defs' instead of '--strict'. "
            "Allow minimal Any types with a threshold (e.g., <=5 Any usages)."
        ),
    ),
    InfeasiblePattern(
        key="sub_second_latency",
        keywords=["<1s", "< 1s", "under 1 second", "sub-second", "sub second",
                  "<500ms", "< 500ms", "under 500ms"],
        reason=(
            "Local vLLM inference is ~4x slower than the Anthropic API. "
            "Sub-second or <500ms latency targets are not achievable."
        ),
        suggested_alternative=(
            "Replace with a relative target such as "
            "'responds within acceptable time for local inference' "
            "or remove the hard latency bound."
        ),
    ),
    InfeasiblePattern(
        key="streaming_token_rate",
        keywords=["tokens/s", "tokens per second", "tok/s"],
        reason=(
            "Token throughput is hardware-dependent on vLLM and will differ "
            "substantially from cloud benchmarks."
        ),
        suggested_alternative=(
            "Express the criterion in terms of observable output quality "
            "rather than throughput numbers."
        ),
    ),
    InfeasiblePattern(
        key="cloud_only_feature",
        keywords=["claude.ai", "anthropic console", "aws bedrock", "vertex ai",
                  "amazon bedrock"],
        reason=(
            "This AC references a cloud-specific endpoint or console "
            "that is unavailable on a local vLLM backend."
        ),
        suggested_alternative=(
            "Gate the criterion on backend type, or mark it as "
            "'cloud-only, skip on local' in the test plan."
        ),
    ),
    InfeasiblePattern(
        key="concurrent_requests",
        keywords=["1000 concurrent", "10000 concurrent", "high concurrency",
                  ">500 rps", "> 500 rps"],
        reason=(
            "High concurrency targets assume cloud-scale infrastructure. "
            "Local vLLM is single-node and cannot sustain these loads."
        ),
        suggested_alternative=(
            "Parameterise the concurrency target by backend, "
            "e.g. 'handles N concurrent requests where N=10 on local, N=1000 on cloud'."
        ),
    ),
    InfeasiblePattern(
        key="100_percent_coverage",
        keywords=["100% coverage", "100% test coverage", "100% line coverage",
                  "100% branch coverage"],
        reason=(
            "100% coverage targets are impractical with local vLLM-generated code "
            "due to less precise code generation and longer iteration cycles."
        ),
        suggested_alternative=(
            "Use '>=85% line coverage, >=75% branch coverage' as targets, "
            "consistent with GuardKit quality gate defaults."
        ),
    ),
]

# Backend-specific feasibility score for matched patterns
_VLLM_FEASIBILITY_SCORE = 2  # Low feasibility on vLLM


def detect_backend(timeout_multiplier: Optional[float] = None) -> BackendKind:
    """Derive the active backend from the timeout multiplier.

    Uses detect_timeout_multiplier() from agent_invoker when no override
    is provided. Returns LOCAL_VLLM when multiplier >= 2.0, CLOUD otherwise.

    The threshold of 2.0 is safe: auto-detected values are 1.0 (cloud)
    and 4.0 (local).

    Args:
        timeout_multiplier: Override value. If None, auto-detects.

    Returns:
        BackendKind enum value.
    """
    if timeout_multiplier is None:
        timeout_multiplier = detect_timeout_multiplier()

    if timeout_multiplier >= 2.0:
        return BackendKind.LOCAL_VLLM
    return BackendKind.CLOUD


def _match_criterion(
    criterion: str,
    patterns: list[InfeasiblePattern],
) -> list[InfeasiblePattern]:
    """Check a single criterion against all infeasible patterns.

    Uses case-insensitive substring matching against keyword lists.
    Returns all matching patterns (a criterion may trigger multiple).

    Args:
        criterion: The acceptance criterion text.
        patterns: List of infeasible patterns to check against.

    Returns:
        List of matching InfeasiblePatterns (empty if no match).
    """
    criterion_lower = criterion.lower()
    matched: list[InfeasiblePattern] = []
    for pattern in patterns:
        for keyword in pattern.keywords:
            if keyword.lower() in criterion_lower:
                matched.append(pattern)
                break  # One keyword match per pattern is sufficient
    return matched


def validate_acceptance_criteria(
    criteria: list[str],
    backend: Optional[BackendKind] = None,
) -> ACValidationResult:
    """Check a list of acceptance criteria for backend-infeasible patterns.

    For CLOUD backends, returns immediately with no warnings (all patterns
    are feasible on cloud). For LOCAL_VLLM backends, checks each criterion
    against known infeasible patterns and returns warnings with suggestions.

    Args:
        criteria: List of AC strings from the feature-plan spec.
        backend: Override backend detection. If None, auto-detects.

    Returns:
        ACValidationResult with zero or more ACWarning entries.
    """
    if backend is None:
        backend = detect_backend()

    result = ACValidationResult(backend=backend)

    # Cloud backends have no known infeasible patterns
    if backend == BackendKind.CLOUD:
        return result

    # UNKNOWN backend gets conservative (same as vLLM) treatment
    patterns = VLLM_INFEASIBLE_PATTERNS

    for criterion in criteria:
        if not criterion.strip():
            continue
        matched_patterns = _match_criterion(criterion, patterns)
        for matched in matched_patterns:
            result.warnings.append(
                ACWarning(
                    criterion=criterion,
                    matched_pattern=matched.key,
                    reason=matched.reason,
                    suggested_alternative=matched.suggested_alternative,
                    feasibility_score=_VLLM_FEASIBILITY_SCORE,
                )
            )

    return result


def format_validation_report(result: ACValidationResult) -> str:
    """Render ACValidationResult as a human-readable warning block.

    Returns an empty string when result.has_warnings is False.
    Intended for direct print() output in the feature-plan workflow.

    Args:
        result: The validation result to format.

    Returns:
        Formatted string with warnings and suggestions, or empty string.
    """
    if not result.has_warnings:
        return ""

    lines: list[str] = []
    lines.append("")
    lines.append("=" * 60)
    lines.append(
        f"  AC FEASIBILITY WARNINGS ({result.flagged_count} issue(s) "
        f"for {result.backend.value} backend)"
    )
    lines.append("=" * 60)

    for i, warning in enumerate(result.warnings, 1):
        lines.append("")
        lines.append(f"  {i}. Criterion: {warning.criterion}")
        lines.append(f"     Pattern: {warning.matched_pattern}")
        lines.append(f"     Feasibility: {warning.feasibility_score}/10")
        lines.append(f"     Reason: {warning.reason}")
        lines.append(f"     Suggestion: {warning.suggested_alternative}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(
        "  These warnings are advisory. Feature planning will continue."
    )
    lines.append("-" * 60)
    lines.append("")

    return "\n".join(lines)
