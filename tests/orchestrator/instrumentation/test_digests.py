"""Tests for role-specific digest system.

Covers DigestValidator, DigestLoader, PromptProfile, and digest file validation.
TDD RED phase: these tests are written before the implementation.

Acceptance criteria covered:
- AC-001: Four digest files created (player, coach, resolver, router)
- AC-002: Each digest under 700 tokens
- AC-003: DigestValidator accepts exactly 700 tokens, warns at 701+
- AC-004: Missing digest file produces clear error (no silent fallback)
- AC-005: DigestLoader returns correct digest for each role
- AC-006: Prompt profile switching supports all four profiles
- AC-007: Phase 1: full rules bundle injected alongside digest
- AC-008: No two digests are identical
- AC-009: Token counting implemented (tiktoken or word-based fallback)
- AC-010: Digest content is stack-agnostic
- AC-011: Unit tests cover validation boundaries (700/701), loading, profiles
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

from guardkit.orchestrator.instrumentation.digests import (
    DigestLoader,
    DigestLoadError,
    DigestValidator,
    DigestValidationResult,
    count_tokens,
    DIGEST_ROLES,
    MAX_TOKENS,
)
from guardkit.orchestrator.instrumentation.prompt_profile import (
    PromptProfile,
    PromptProfileAssembler,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def digest_dir(tmp_path: Path) -> Path:
    """Create a temporary digest directory with valid digest files."""
    digests_dir = tmp_path / ".guardkit" / "digests"
    digests_dir.mkdir(parents=True)

    # Create minimal valid digest files (well under 700 tokens)
    for role in ["player", "coach", "resolver", "router"]:
        content = f"# {role.title()} Digest\n\nRole-specific rules for {role}.\n"
        (digests_dir / f"{role}.md").write_text(content)

    return digests_dir


@pytest.fixture
def real_digest_dir() -> Path:
    """Return the path to actual digest files in the project."""
    return Path(__file__).parent.parent.parent.parent / ".guardkit" / "digests"


@pytest.fixture
def validator(digest_dir: Path) -> DigestValidator:
    """Create a DigestValidator for the test digest directory."""
    return DigestValidator(digest_dir)


@pytest.fixture
def loader(digest_dir: Path) -> DigestLoader:
    """Create a DigestLoader for the test digest directory."""
    return DigestLoader(digest_dir)


# ============================================================================
# Token Counting Tests (AC-009)
# ============================================================================


class TestTokenCounting:
    """Tests for token counting implementation."""

    def test_count_tokens_returns_int(self) -> None:
        """count_tokens returns an integer."""
        result = count_tokens("Hello world")
        assert isinstance(result, int)

    def test_count_tokens_empty_string(self) -> None:
        """Empty string yields zero tokens."""
        assert count_tokens("") == 0

    def test_count_tokens_single_word(self) -> None:
        """Single word yields at least 1 token."""
        assert count_tokens("hello") >= 1

    def test_count_tokens_multiple_words(self) -> None:
        """Multiple words yield proportionally more tokens."""
        short = count_tokens("hello")
        long = count_tokens("hello world this is a longer sentence with more words")
        assert long > short

    def test_count_tokens_handles_markdown(self) -> None:
        """Token counter handles markdown content."""
        md = "# Heading\n\n- Item 1\n- Item 2\n\n**bold** and *italic*"
        result = count_tokens(md)
        assert result > 0

    def test_word_based_fallback_approximation(self) -> None:
        """Word-based fallback provides reasonable approximation.

        The standard approximation is ~0.75 tokens per word (4 chars/token).
        A 100-word text should yield roughly 75-150 tokens.
        """
        words = " ".join(["word"] * 100)
        result = count_tokens(words)
        # Reasonable range for 100 words
        assert 50 <= result <= 200


# ============================================================================
# DigestValidator Tests (AC-002, AC-003, AC-004, AC-009)
# ============================================================================


class TestDigestValidator:
    """Tests for DigestValidator."""

    def test_validate_all_valid(self, validator: DigestValidator) -> None:
        """Validator accepts all valid digest files."""
        results = validator.validate_all()
        assert all(r.valid for r in results)

    def test_validate_single_role(self, validator: DigestValidator) -> None:
        """Validator can validate a single role's digest."""
        result = validator.validate("player")
        assert result.valid is True
        assert result.role == "player"

    def test_validate_returns_token_count(self, validator: DigestValidator) -> None:
        """Validation result includes token count."""
        result = validator.validate("player")
        assert result.token_count > 0

    def test_exactly_700_tokens_accepted(self, tmp_path: Path) -> None:
        """Digest with exactly 700 tokens is accepted without warning (AC-003)."""
        digests_dir = tmp_path / "digests"
        digests_dir.mkdir()
        # Create content that's exactly at the boundary
        # We'll generate text and use count_tokens to calibrate
        content = _generate_content_with_token_count(700)
        (digests_dir / "player.md").write_text(content)

        v = DigestValidator(digests_dir)
        result = v.validate("player")
        assert result.valid is True
        assert result.warning is None

    def test_701_tokens_warns(self, tmp_path: Path) -> None:
        """Digest with 701+ tokens produces a warning (AC-003)."""
        digests_dir = tmp_path / "digests"
        digests_dir.mkdir()
        content = _generate_content_with_token_count(750)
        (digests_dir / "player.md").write_text(content)

        v = DigestValidator(digests_dir)
        result = v.validate("player")
        assert result.valid is True  # Still valid, just warned
        assert result.warning is not None
        assert "exceeds" in result.warning.lower() or "maximum" in result.warning.lower()

    def test_missing_digest_raises_error(self, tmp_path: Path) -> None:
        """Missing digest file produces clear error (AC-004)."""
        digests_dir = tmp_path / "empty_digests"
        digests_dir.mkdir()

        v = DigestValidator(digests_dir)
        with pytest.raises(DigestLoadError) as exc_info:
            v.validate("player")
        assert "player" in str(exc_info.value).lower()

    def test_missing_digest_no_silent_fallback(self, tmp_path: Path) -> None:
        """Missing digest does NOT silently fallback (AC-004)."""
        digests_dir = tmp_path / "empty_digests"
        digests_dir.mkdir()

        v = DigestValidator(digests_dir)
        # Should raise, not return empty or default content
        with pytest.raises(DigestLoadError):
            v.validate("player")

    def test_invalid_role_rejected(self, validator: DigestValidator) -> None:
        """Invalid role name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            validator.validate("wizard")

    def test_validate_all_checks_all_roles(self, validator: DigestValidator) -> None:
        """validate_all checks all four roles."""
        results = validator.validate_all()
        roles = {r.role for r in results}
        assert roles == {"player", "coach", "resolver", "router"}

    def test_max_tokens_constant(self) -> None:
        """MAX_TOKENS is set to 700."""
        assert MAX_TOKENS == 700


# ============================================================================
# DigestValidationResult Tests
# ============================================================================


class TestDigestValidationResult:
    """Tests for DigestValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Valid result has expected fields."""
        result = DigestValidationResult(
            role="player",
            valid=True,
            token_count=300,
            warning=None,
        )
        assert result.role == "player"
        assert result.valid is True
        assert result.token_count == 300
        assert result.warning is None

    def test_warned_result(self) -> None:
        """Result with warning."""
        result = DigestValidationResult(
            role="coach",
            valid=True,
            token_count=720,
            warning="Digest exceeds maximum of 700 tokens",
        )
        assert result.warning is not None


# ============================================================================
# DigestLoader Tests (AC-005)
# ============================================================================


class TestDigestLoader:
    """Tests for DigestLoader."""

    def test_load_player_digest(self, loader: DigestLoader) -> None:
        """Loader returns player digest content."""
        content = loader.load("player")
        assert isinstance(content, str)
        assert len(content) > 0
        assert "player" in content.lower()

    def test_load_coach_digest(self, loader: DigestLoader) -> None:
        """Loader returns coach digest content."""
        content = loader.load("coach")
        assert isinstance(content, str)
        assert "coach" in content.lower()

    def test_load_resolver_digest(self, loader: DigestLoader) -> None:
        """Loader returns resolver digest content."""
        content = loader.load("resolver")
        assert isinstance(content, str)
        assert "resolver" in content.lower()

    def test_load_router_digest(self, loader: DigestLoader) -> None:
        """Loader returns router digest content."""
        content = loader.load("router")
        assert isinstance(content, str)
        assert "router" in content.lower()

    def test_load_correct_content_per_role(self, digest_dir: Path) -> None:
        """Each role gets its own specific content (AC-005)."""
        loader = DigestLoader(digest_dir)
        contents = {role: loader.load(role) for role in DIGEST_ROLES}
        # All should be different
        unique_contents = set(contents.values())
        assert len(unique_contents) == 4, "All four digests must be unique"

    def test_load_missing_digest_raises_error(self, tmp_path: Path) -> None:
        """Loading missing digest raises DigestLoadError (AC-004)."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        loader = DigestLoader(empty_dir)
        with pytest.raises(DigestLoadError):
            loader.load("player")

    def test_load_invalid_role_raises_error(self, loader: DigestLoader) -> None:
        """Loading with invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            loader.load("wizard")

    def test_load_returns_string(self, loader: DigestLoader) -> None:
        """Loaded digest is a string suitable for prompt injection."""
        content = loader.load("player")
        assert isinstance(content, str)


# ============================================================================
# PromptProfile Tests (AC-006, AC-007)
# ============================================================================


class TestPromptProfile:
    """Tests for PromptProfile enum."""

    def test_digest_only_profile(self) -> None:
        """digest_only profile exists."""
        assert PromptProfile.DIGEST_ONLY.value == "digest_only"

    def test_digest_graphiti_profile(self) -> None:
        """digest+graphiti profile exists."""
        assert PromptProfile.DIGEST_GRAPHITI.value == "digest+graphiti"

    def test_digest_rules_bundle_profile(self) -> None:
        """digest+rules_bundle profile exists."""
        assert PromptProfile.DIGEST_RULES_BUNDLE.value == "digest+rules_bundle"

    def test_digest_graphiti_rules_bundle_profile(self) -> None:
        """digest+graphiti+rules_bundle profile exists."""
        assert PromptProfile.DIGEST_GRAPHITI_RULES_BUNDLE.value == "digest+graphiti+rules_bundle"

    def test_all_four_profiles_exist(self) -> None:
        """All four profiles are defined (AC-006)."""
        profiles = list(PromptProfile)
        assert len(profiles) == 4


# ============================================================================
# PromptProfileAssembler Tests (AC-006, AC-007)
# ============================================================================


class TestPromptProfileAssembler:
    """Tests for PromptProfileAssembler."""

    def test_digest_only_returns_digest_content(self, loader: DigestLoader) -> None:
        """digest_only profile returns only digest content."""
        assembler = PromptProfileAssembler(loader=loader)
        result = assembler.assemble(
            role="player",
            profile=PromptProfile.DIGEST_ONLY,
        )
        assert len(result) > 0
        # Should NOT contain rules bundle marker
        assert "[RULES_BUNDLE]" not in result

    def test_digest_rules_bundle_includes_both(self, loader: DigestLoader) -> None:
        """digest+rules_bundle includes digest AND rules bundle (AC-007)."""
        rules_bundle = "## Full Rules Bundle\n\nThis is the full rules content."
        assembler = PromptProfileAssembler(loader=loader)
        result = assembler.assemble(
            role="player",
            profile=PromptProfile.DIGEST_RULES_BUNDLE,
            rules_bundle=rules_bundle,
        )
        # Should contain digest content
        assert "player" in result.lower()
        # Should contain rules bundle
        assert "Full Rules Bundle" in result

    def test_digest_graphiti_includes_context(self, loader: DigestLoader) -> None:
        """digest+graphiti includes digest AND graphiti context."""
        graphiti_context = "## Retrieved Context\n\nSome knowledge graph data."
        assembler = PromptProfileAssembler(loader=loader)
        result = assembler.assemble(
            role="player",
            profile=PromptProfile.DIGEST_GRAPHITI,
            graphiti_context=graphiti_context,
        )
        assert "player" in result.lower()
        assert "Retrieved Context" in result

    def test_digest_graphiti_rules_bundle_includes_all(self, loader: DigestLoader) -> None:
        """digest+graphiti+rules_bundle includes all three (transitional)."""
        rules_bundle = "## Rules Bundle"
        graphiti_context = "## Graphiti Context"
        assembler = PromptProfileAssembler(loader=loader)
        result = assembler.assemble(
            role="player",
            profile=PromptProfile.DIGEST_GRAPHITI_RULES_BUNDLE,
            rules_bundle=rules_bundle,
            graphiti_context=graphiti_context,
        )
        assert "player" in result.lower()
        assert "Rules Bundle" in result
        assert "Graphiti Context" in result

    def test_default_profile_is_digest_rules_bundle(self, loader: DigestLoader) -> None:
        """Default profile is digest+rules_bundle (Phase 1 migration, AC-007)."""
        assembler = PromptProfileAssembler(loader=loader)
        assert assembler.default_profile == PromptProfile.DIGEST_RULES_BUNDLE

    def test_active_profile_reported(self, loader: DigestLoader) -> None:
        """Assembler reports the active profile for instrumentation tagging."""
        assembler = PromptProfileAssembler(loader=loader)
        result = assembler.assemble(
            role="player",
            profile=PromptProfile.DIGEST_ONLY,
        )
        assert assembler.last_profile == PromptProfile.DIGEST_ONLY


# ============================================================================
# Real Digest File Tests (AC-001, AC-002, AC-008, AC-010)
# ============================================================================


class TestRealDigestFiles:
    """Tests that validate the actual digest files in the project."""

    def test_all_four_digest_files_exist(self, real_digest_dir: Path) -> None:
        """All four digest files exist (AC-001)."""
        for role in ["player", "coach", "resolver", "router"]:
            path = real_digest_dir / f"{role}.md"
            assert path.exists(), f"Missing digest file: {role}.md"

    def test_each_digest_under_700_tokens(self, real_digest_dir: Path) -> None:
        """Each digest is under 700 tokens (AC-002)."""
        for role in ["player", "coach", "resolver", "router"]:
            path = real_digest_dir / f"{role}.md"
            content = path.read_text()
            tokens = count_tokens(content)
            assert tokens <= 700, (
                f"{role}.md has {tokens} tokens, exceeds 700 limit"
            )

    def test_no_two_digests_identical(self, real_digest_dir: Path) -> None:
        """No two digests are identical (AC-008)."""
        contents = {}
        for role in ["player", "coach", "resolver", "router"]:
            path = real_digest_dir / f"{role}.md"
            contents[role] = path.read_text()

        # Check all pairs
        roles = list(contents.keys())
        for i in range(len(roles)):
            for j in range(i + 1, len(roles)):
                assert contents[roles[i]] != contents[roles[j]], (
                    f"{roles[i]}.md and {roles[j]}.md are identical"
                )

    def test_digests_are_stack_agnostic(self, real_digest_dir: Path) -> None:
        """Digest content is stack-agnostic (AC-010).

        Must NOT reference specific tools, test frameworks, or language idioms.
        """
        stack_specific_patterns = [
            r"\bpytest\b",
            r"\bnpm\b",
            r"\bdotnet\b",
            r"\bcargo\b",
            r"\bgo test\b",
            r"\bvitest\b",
            r"\bjest\b",
            r"\bmocha\b",
            r"\bxunit\b",
            r"\bnunit\b",
            r"\bpython\b",
            r"\btypescript\b",
            r"\bjavascript\b",
            r"\brust\b",
            r"\bc#\b",
            r"\bpip\b",
            r"\byarn\b",
            r"\bpnpm\b",
        ]

        for role in ["player", "coach", "resolver", "router"]:
            path = real_digest_dir / f"{role}.md"
            content = path.read_text().lower()
            for pattern in stack_specific_patterns:
                assert not re.search(pattern, content), (
                    f"{role}.md contains stack-specific reference matching '{pattern}'"
                )

    def test_digests_non_empty(self, real_digest_dir: Path) -> None:
        """All digest files have meaningful content."""
        for role in ["player", "coach", "resolver", "router"]:
            path = real_digest_dir / f"{role}.md"
            content = path.read_text().strip()
            assert len(content) > 50, (
                f"{role}.md is too short ({len(content)} chars)"
            )

    def test_digests_have_minimum_token_count(self, real_digest_dir: Path) -> None:
        """Each digest has at least 100 tokens (meaningful content, ~300-600 target)."""
        for role in ["player", "coach", "resolver", "router"]:
            path = real_digest_dir / f"{role}.md"
            content = path.read_text()
            tokens = count_tokens(content)
            assert tokens >= 100, (
                f"{role}.md has only {tokens} tokens, expected >= 100"
            )


# ============================================================================
# DIGEST_ROLES Constant Tests
# ============================================================================


class TestDigestRoles:
    """Tests for DIGEST_ROLES constant."""

    def test_digest_roles_has_four_entries(self) -> None:
        """DIGEST_ROLES has exactly four entries."""
        assert len(DIGEST_ROLES) == 4

    def test_digest_roles_values(self) -> None:
        """DIGEST_ROLES contains the expected roles."""
        assert set(DIGEST_ROLES) == {"player", "coach", "resolver", "router"}


# ============================================================================
# Helpers
# ============================================================================


def _generate_content_with_token_count(target_tokens: int) -> str:
    """Generate markdown content with approximately the target token count.

    Uses count_tokens to calibrate the output. This is iterative:
    starts with a word-count estimate and adjusts.
    """
    # Word-based approximation: ~1.33 words per token (inverse of 0.75)
    estimated_words = int(target_tokens * 1.33)
    words = ["word"] * estimated_words
    content = " ".join(words)

    # Adjust iteratively
    current = count_tokens(content)
    if current < target_tokens:
        # Add more words
        while count_tokens(content) < target_tokens:
            content += " extra"
    elif current > target_tokens:
        # Trim words
        word_list = content.split()
        while count_tokens(" ".join(word_list)) > target_tokens and len(word_list) > 1:
            word_list.pop()
        content = " ".join(word_list)

    return content
