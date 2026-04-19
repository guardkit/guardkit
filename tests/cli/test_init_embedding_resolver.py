"""
Tests for ``_resolve_embedding_dimensions`` in ``guardkit.cli.init``.

Covers R2 / R3 / R4 from TASK-REV-E8D1:
  * Tier 1 — explicit ``settings.embedding_dimensions`` is respected.
  * Tier 2 — model lookup via ``KNOWN_EMBEDDING_DIMS``.
  * Tier 3 — final fallback to 1536 for unknown models.
  * Warning emission only on the tier-3 fallback path.

Coverage Target: >=95% for the resolver function.
"""

from unittest.mock import MagicMock, patch

import pytest

from guardkit.cli.init import _resolve_embedding_dimensions


def _settings(embedding_model=None, embedding_dimensions=None):
    """Minimal settings double exposing the two attrs the resolver reads."""
    s = MagicMock()
    s.embedding_model = embedding_model
    s.embedding_dimensions = embedding_dimensions
    return s


# ============================================================================
# Tier 2 — known model lookup
# ============================================================================


class TestResolverKnownModel:
    def test_nomic_resolves_to_768(self):
        assert _resolve_embedding_dimensions(
            _settings(embedding_model="nomic-embed-text-v1.5")
        ) == 768

    def test_ada_002_resolves_to_1536(self):
        assert _resolve_embedding_dimensions(
            _settings(embedding_model="text-embedding-ada-002")
        ) == 1536

    def test_text_embedding_3_large_resolves_to_3072(self):
        assert _resolve_embedding_dimensions(
            _settings(embedding_model="text-embedding-3-large")
        ) == 3072


# ============================================================================
# Tier 3 — unknown model falls back to 1536
# ============================================================================


class TestResolverUnknownModel:
    def test_unknown_model_falls_back_to_1536(self):
        assert _resolve_embedding_dimensions(
            _settings(embedding_model="unknown-future-model")
        ) == 1536

    def test_empty_model_falls_back_to_1536(self):
        assert _resolve_embedding_dimensions(
            _settings(embedding_model="")
        ) == 1536

    def test_none_model_falls_back_to_1536(self):
        assert _resolve_embedding_dimensions(
            _settings(embedding_model=None)
        ) == 1536


# ============================================================================
# Tier 1 — explicit override wins over model lookup
# ============================================================================


class TestResolverExplicitOverride:
    def test_explicit_override_wins_over_known_model(self):
        # Known model would give 768, but explicit override is 256.
        assert _resolve_embedding_dimensions(
            _settings(embedding_model="nomic-embed-text-v1.5",
                      embedding_dimensions=256)
        ) == 256

    def test_explicit_override_wins_over_unknown_model(self):
        assert _resolve_embedding_dimensions(
            _settings(embedding_model="unknown-future-model",
                      embedding_dimensions=256)
        ) == 256

    def test_explicit_zero_is_respected(self):
        # 0 is falsy but not None, so the resolver must honour it rather
        # than dropping through to tier 2/3. This is the regression that
        # motivated replacing ``or 1024`` with an explicit ``is not None``
        # check.
        assert _resolve_embedding_dimensions(
            _settings(embedding_model="nomic-embed-text-v1.5",
                      embedding_dimensions=0)
        ) == 0


# ============================================================================
# Repurposed warning — fires only on tier-3 fallback
# ============================================================================


class TestRepurposedWarning:
    """
    The warning at ``init.py`` inside ``_do_init_mcp_writes`` (around the
    ``write_mcp_json`` call) should fire only when both:
      * ``settings.embedding_dimensions`` is None, and
      * ``settings.embedding_model`` is not in ``KNOWN_EMBEDDING_DIMS``.

    It must stay silent for tier 1 (explicit) and tier 2 (known model).
    We assert the condition directly against the module-level table rather
    than driving the full CLI, keeping the test fast and isolated.
    """

    def test_warning_condition_true_for_unknown_model(self):
        from guardkit.knowledge.graphiti_client import KNOWN_EMBEDDING_DIMS
        settings = _settings(embedding_model="unknown-future-model",
                             embedding_dimensions=None)
        # The warning predicate used in init.py:
        should_warn = (
            settings.embedding_dimensions is None
            and settings.embedding_model
            and settings.embedding_model not in KNOWN_EMBEDDING_DIMS
        )
        assert should_warn is True

    def test_warning_condition_false_for_known_model(self):
        from guardkit.knowledge.graphiti_client import KNOWN_EMBEDDING_DIMS
        settings = _settings(embedding_model="nomic-embed-text-v1.5",
                             embedding_dimensions=None)
        should_warn = (
            settings.embedding_dimensions is None
            and settings.embedding_model
            and settings.embedding_model not in KNOWN_EMBEDDING_DIMS
        )
        assert should_warn is False

    def test_warning_condition_false_when_explicit_override_set(self):
        from guardkit.knowledge.graphiti_client import KNOWN_EMBEDDING_DIMS
        settings = _settings(embedding_model="unknown-future-model",
                             embedding_dimensions=1024)
        should_warn = (
            settings.embedding_dimensions is None
            and settings.embedding_model
            and settings.embedding_model not in KNOWN_EMBEDDING_DIMS
        )
        assert should_warn is False
