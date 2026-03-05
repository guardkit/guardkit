"""Tests for ArchitecturalDecisionEpisode schema.

Coverage Target: >=85%
"""

import pytest
from dataclasses import asdict

from guardkit.integrations.graphiti.episodes.architectural_decision import (
    ArchitecturalDecisionEpisode,
    ARCHITECTURAL_DECISION_DEFAULTS,
)


class TestArchitecturalDecisionEpisodeInstantiation:
    """Test basic instantiation with default and custom values."""

    def test_instantiate_with_defaults(self):
        """Should create instance with all default values."""
        episode = ArchitecturalDecisionEpisode()

        assert episode.entity_type == "architectural_decision"
        assert episode.title == ""
        assert episode.summary == ""
        assert episode.implications == []
        assert episode.evidence == ""
        assert episode.decision_reference == ""
        assert episode.date == ""

    def test_instantiate_with_all_fields(self):
        """Should create instance with all fields populated."""
        episode = ArchitecturalDecisionEpisode(
            title="Test Decision",
            summary="A test decision summary",
            implications=["Implication 1", "Implication 2"],
            evidence="docs/test.md",
            decision_reference="TASK-TEST-001",
            date="2026-02-05",
        )

        assert episode.title == "Test Decision"
        assert episode.summary == "A test decision summary"
        assert len(episode.implications) == 2
        assert episode.evidence == "docs/test.md"
        assert episode.decision_reference == "TASK-TEST-001"
        assert episode.date == "2026-02-05"


class TestArchitecturalDecisionEpisodeEntityId:
    """Test entity ID generation for Graphiti upsert."""

    def test_get_entity_id_basic(self):
        """Should generate stable entity ID from title."""
        episode = ArchitecturalDecisionEpisode(title="My Decision")
        entity_id = episode.get_entity_id()

        assert entity_id.startswith("arch_decision_")
        assert "my_decision" in entity_id

    def test_get_entity_id_stability(self):
        """Same title should always generate same entity ID."""
        ep1 = ArchitecturalDecisionEpisode(title="Test Decision")
        ep2 = ArchitecturalDecisionEpisode(
            title="Test Decision", summary="Different summary"
        )

        assert ep1.get_entity_id() == ep2.get_entity_id()

    def test_get_entity_id_truncates_long_titles(self):
        """Should truncate very long titles in entity ID."""
        long_title = "A" * 100
        episode = ArchitecturalDecisionEpisode(title=long_title)
        entity_id = episode.get_entity_id()

        # Prefix + 60 char slug max
        assert len(entity_id) <= len("arch_decision_") + 60


class TestArchitecturalDecisionEpisodeToEpisodeContent:
    """Test conversion to natural language for Graphiti."""

    def test_to_episode_content_contains_title(self):
        """Should include the decision title."""
        episode = ArchitecturalDecisionEpisode(
            title="Graphiti Fidelity Limitation",
            summary="Test summary",
        )
        content = episode.to_episode_content()

        assert "Graphiti Fidelity Limitation" in content

    def test_to_episode_content_contains_summary(self):
        """Should include the summary."""
        episode = ArchitecturalDecisionEpisode(
            title="Test", summary="This is the summary text"
        )
        content = episode.to_episode_content()

        assert "This is the summary text" in content

    def test_to_episode_content_contains_implications(self):
        """Should include all implications."""
        episode = ArchitecturalDecisionEpisode(
            title="Test",
            implications=["Do not do X", "Always prefer Y"],
        )
        content = episode.to_episode_content()

        assert "Do not do X" in content
        assert "Always prefer Y" in content

    def test_to_episode_content_contains_evidence(self):
        """Should include evidence reference."""
        episode = ArchitecturalDecisionEpisode(
            title="Test", evidence="docs/reviews/test.md"
        )
        content = episode.to_episode_content()

        assert "docs/reviews/test.md" in content

    def test_to_episode_content_contains_date(self):
        """Should include the decision date."""
        episode = ArchitecturalDecisionEpisode(title="Test", date="2026-02-05")
        content = episode.to_episode_content()

        assert "2026-02-05" in content


class TestArchitecturalDecisionEpisodeSerialization:
    """Test serialization to dict format."""

    def test_serialization_to_dict(self):
        """Should serialize to dict via asdict."""
        episode = ArchitecturalDecisionEpisode(
            title="Test Decision",
            summary="Summary",
            implications=["A", "B"],
        )
        data = asdict(episode)

        assert isinstance(data, dict)
        assert data["entity_type"] == "architectural_decision"
        assert data["title"] == "Test Decision"
        assert data["implications"] == ["A", "B"]

    def test_serialization_preserves_lists(self):
        """Should preserve list fields in serialization."""
        episode = ArchitecturalDecisionEpisode(
            title="Test", implications=["X", "Y", "Z"]
        )
        data = asdict(episode)

        assert isinstance(data["implications"], list)
        assert len(data["implications"]) == 3


class TestArchitecturalDecisionDefaults:
    """Test the ARCHITECTURAL_DECISION_DEFAULTS constant."""

    def test_defaults_contains_graphiti_fidelity(self):
        """Should contain the graphiti_fidelity_limitation decision."""
        assert "graphiti_fidelity_limitation" in ARCHITECTURAL_DECISION_DEFAULTS

    def test_graphiti_fidelity_has_title(self):
        """Graphiti fidelity decision should have a descriptive title."""
        decision = ARCHITECTURAL_DECISION_DEFAULTS["graphiti_fidelity_limitation"]
        assert "Fidelity" in decision.title or "fidelity" in decision.title

    def test_graphiti_fidelity_has_implications(self):
        """Graphiti fidelity decision should have implications."""
        decision = ARCHITECTURAL_DECISION_DEFAULTS["graphiti_fidelity_limitation"]
        assert len(decision.implications) >= 3

    def test_graphiti_fidelity_has_evidence(self):
        """Graphiti fidelity decision should reference evidence document."""
        decision = ARCHITECTURAL_DECISION_DEFAULTS["graphiti_fidelity_limitation"]
        assert "graphiti_code_retrieval_fidelity" in decision.evidence

    def test_graphiti_fidelity_has_date(self):
        """Graphiti fidelity decision should have a date."""
        decision = ARCHITECTURAL_DECISION_DEFAULTS["graphiti_fidelity_limitation"]
        assert decision.date == "2026-02-05"

    def test_graphiti_fidelity_mentions_code_retrieval(self):
        """Summary should mention code retrieval limitation."""
        decision = ARCHITECTURAL_DECISION_DEFAULTS["graphiti_fidelity_limitation"]
        assert "code" in decision.summary.lower()

    def test_graphiti_fidelity_mentions_semantic_facts(self):
        """Summary should mention semantic facts distinction."""
        decision = ARCHITECTURAL_DECISION_DEFAULTS["graphiti_fidelity_limitation"]
        assert "semantic" in decision.summary.lower() or "facts" in decision.summary.lower()

    def test_all_defaults_are_valid_episodes(self):
        """All defaults should produce valid episode content."""
        for key, decision in ARCHITECTURAL_DECISION_DEFAULTS.items():
            content = decision.to_episode_content()
            assert isinstance(content, str)
            assert len(content) > 0
            entity_id = decision.get_entity_id()
            assert entity_id.startswith("arch_decision_")
