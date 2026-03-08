"""
Content validation tests for role-specific digest files.

Validates that .guardkit/digests/{role}.md files meet TASK-INST-014
acceptance criteria: token budgets, loader/validator integration,
and content accuracy (including FailureCategory vocabulary match).

Coverage Target: >=85%
Test Count: 10+ tests
"""

import re
from pathlib import Path
from typing import get_args

import pytest

from guardkit.orchestrator.instrumentation.digests import (
    DigestLoader,
    DigestValidator,
    count_tokens,
    DIGEST_ROLES,
    MAX_TOKENS,
)
from guardkit.orchestrator.instrumentation.schemas import FailureCategory


@pytest.fixture
def digest_dir() -> Path:
    """Return the path to actual digest files in the project."""
    return Path(__file__).parent.parent.parent.parent / ".guardkit" / "digests"


@pytest.fixture
def loader(digest_dir: Path) -> DigestLoader:
    """Create a DigestLoader for the real digest directory."""
    return DigestLoader(digest_dir)


@pytest.fixture
def validator(digest_dir: Path) -> DigestValidator:
    """Create a DigestValidator for the real digest directory."""
    return DigestValidator(digest_dir)


# ============================================================================
# 1. File Existence and Token Budget Tests
# ============================================================================


class TestDigestTokenBudgets:
    """Verify each digest is within the 300-600 token target range."""

    @pytest.mark.parametrize("role", list(DIGEST_ROLES))
    def test_digest_in_target_token_range(self, digest_dir: Path, role: str) -> None:
        """Each digest is between 300-600 tokens (AC-003)."""
        content = (digest_dir / f"{role}.md").read_text()
        tokens = count_tokens(content)
        assert 300 <= tokens <= 600, (
            f"{role}.md has {tokens} tokens, expected 300-600"
        )

    @pytest.mark.parametrize("role", list(DIGEST_ROLES))
    def test_digest_under_hard_limit(self, digest_dir: Path, role: str) -> None:
        """Each digest is under 700 token hard limit (AC-002)."""
        content = (digest_dir / f"{role}.md").read_text()
        tokens = count_tokens(content)
        assert tokens <= MAX_TOKENS, (
            f"{role}.md has {tokens} tokens, exceeds {MAX_TOKENS} hard limit"
        )


# ============================================================================
# 2. DigestLoader Integration Tests
# ============================================================================


class TestDigestLoaderIntegration:
    """Verify DigestLoader.load() works for all four roles."""

    @pytest.mark.parametrize("role", list(DIGEST_ROLES))
    def test_loader_returns_content(self, loader: DigestLoader, role: str) -> None:
        """DigestLoader.load(role) returns content without raising (AC-004)."""
        content = loader.load(role)
        assert isinstance(content, str)
        assert len(content.strip()) > 0

    @pytest.mark.parametrize("role", list(DIGEST_ROLES))
    def test_loader_content_starts_with_heading(
        self, loader: DigestLoader, role: str
    ) -> None:
        """Each digest starts with a role-specific heading."""
        content = loader.load(role)
        first_line = content.strip().split("\n")[0]
        assert first_line.startswith("# "), (
            f"{role}.md first line is not a heading: {first_line!r}"
        )


# ============================================================================
# 3. DigestValidator Integration Tests
# ============================================================================


class TestDigestValidatorIntegration:
    """Verify DigestValidator.validate_all() passes without warnings."""

    def test_validate_all_passes(self, validator: DigestValidator) -> None:
        """DigestValidator.validate_all() passes without warnings (AC-005)."""
        results = validator.validate_all()
        assert len(results) == len(DIGEST_ROLES)
        for result in results:
            assert result.valid, f"{result.role}.md validation failed"
            assert result.warning is None, (
                f"{result.role}.md has warning: {result.warning}"
            )

    @pytest.mark.parametrize("role", list(DIGEST_ROLES))
    def test_validate_individual_role(
        self, validator: DigestValidator, role: str
    ) -> None:
        """Each role validates individually without warning."""
        result = validator.validate(role)
        assert result.valid
        assert result.warning is None
        assert result.token_count > 0


# ============================================================================
# 4. Content Accuracy Tests
# ============================================================================


class TestDigestContentAccuracy:
    """Verify content accurately reflects role descriptions (AC-006)."""

    def test_player_has_output_contract(self, digest_dir: Path) -> None:
        """Player digest includes output contract fields."""
        content = (digest_dir / "player.md").read_text()
        assert "## Output Contract" in content
        for field in ["Summary", "Files changed", "How to verify", "Risks"]:
            assert field in content, f"Player missing output field: {field}"

    def test_coach_has_output_contract(self, digest_dir: Path) -> None:
        """Coach digest includes output contract fields."""
        content = (digest_dir / "coach.md").read_text()
        assert "## Output Contract" in content
        for field in ["Verdict", "Failure category", "Issues list", "Next action"]:
            assert field in content, f"Coach missing output field: {field}"

    def test_resolver_has_remediation_format(self, digest_dir: Path) -> None:
        """Resolver digest includes remediation plan fields."""
        content = (digest_dir / "resolver.md").read_text()
        for field in ["Root cause", "Remediation steps", "Context to persist"]:
            assert field in content, f"Resolver missing field: {field}"

    def test_router_has_routing_format(self, digest_dir: Path) -> None:
        """Router digest includes routing decision fields."""
        content = (digest_dir / "router.md").read_text()
        for field in ["Selected model", "Rationale", "Escalation flag"]:
            assert field in content, f"Router missing field: {field}"

    def test_player_has_minimal_changes_directive(self, digest_dir: Path) -> None:
        """Player digest instructs minimal, focused changes."""
        content = (digest_dir / "player.md").read_text().lower()
        assert "minimal" in content

    def test_resolver_has_retrieval_first_directive(self, digest_dir: Path) -> None:
        """Resolver digest instructs retrieval-first approach."""
        content = (digest_dir / "resolver.md").read_text().lower()
        assert "retrieval" in content

    def test_router_has_smallest_model_directive(self, digest_dir: Path) -> None:
        """Router digest instructs defaulting to smallest capable model."""
        content = (digest_dir / "router.md").read_text().lower()
        assert "smallest" in content


# ============================================================================
# 5. FailureCategory Vocabulary Match (AC-007)
# ============================================================================


class TestCoachFailureCategoryVocabulary:
    """Verify coach.md failure categories match FailureCategory in schemas.py."""

    def test_all_failure_categories_present(self, digest_dir: Path) -> None:
        """Coach digest lists all FailureCategory values (AC-007)."""
        content = (digest_dir / "coach.md").read_text()
        categories = list(get_args(FailureCategory))

        for category in categories:
            assert category in content, (
                f"Coach digest missing FailureCategory: {category}"
            )

    def test_no_extra_categories(self, digest_dir: Path) -> None:
        """Coach digest does not invent categories not in FailureCategory."""
        content = (digest_dir / "coach.md").read_text()
        valid_categories = set(get_args(FailureCategory))

        # Extract underscore_separated words that look like category names
        # from the line that lists the controlled vocabulary
        for line in content.split("\n"):
            if "controlled vocabulary" in line.lower() or "failure categor" in line.lower():
                # Find all snake_case tokens in this line
                found = re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", line)
                for token in found:
                    assert token in valid_categories, (
                        f"Coach digest has unknown category: {token}"
                    )
