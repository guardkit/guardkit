"""Tests for parser base classes.

TDD RED Phase: These tests define the expected behavior for:
- EpisodeData dataclass
- ParseResult dataclass
- BaseParser abstract class
"""

import pytest
from dataclasses import fields

# These imports will fail until implementation is complete (TDD RED)
from guardkit.integrations.graphiti.parsers.base import (
    EpisodeData,
    ParseResult,
    BaseParser,
)


class TestEpisodeData:
    """Tests for EpisodeData dataclass."""

    def test_episode_data_is_dataclass(self):
        """EpisodeData should be a dataclass."""
        assert hasattr(EpisodeData, "__dataclass_fields__")

    def test_episode_data_has_required_fields(self):
        """EpisodeData should have content, group_id, entity_type, entity_id, metadata."""
        field_names = {f.name for f in fields(EpisodeData)}
        required_fields = {"content", "group_id", "entity_type", "entity_id", "metadata"}
        assert required_fields.issubset(field_names)

    def test_episode_data_creation(self):
        """Should be able to create an EpisodeData instance."""
        episode = EpisodeData(
            content="Test content",
            group_id="test-group",
            entity_type="document",
            entity_id="doc-123",
            metadata={"key": "value"},
        )
        assert episode.content == "Test content"
        assert episode.group_id == "test-group"
        assert episode.entity_type == "document"
        assert episode.entity_id == "doc-123"
        assert episode.metadata == {"key": "value"}

    def test_episode_data_with_empty_metadata(self):
        """Should be able to create EpisodeData with empty metadata."""
        episode = EpisodeData(
            content="Content",
            group_id="group",
            entity_type="type",
            entity_id="id",
            metadata={},
        )
        assert episode.metadata == {}

    def test_episode_data_equality(self):
        """Two EpisodeData with same values should be equal."""
        ep1 = EpisodeData(
            content="Test",
            group_id="grp",
            entity_type="type",
            entity_id="id",
            metadata={},
        )
        ep2 = EpisodeData(
            content="Test",
            group_id="grp",
            entity_type="type",
            entity_id="id",
            metadata={},
        )
        assert ep1 == ep2


class TestParseResult:
    """Tests for ParseResult dataclass."""

    def test_parse_result_is_dataclass(self):
        """ParseResult should be a dataclass."""
        assert hasattr(ParseResult, "__dataclass_fields__")

    def test_parse_result_has_required_fields(self):
        """ParseResult should have episodes, warnings, success."""
        field_names = {f.name for f in fields(ParseResult)}
        required_fields = {"episodes", "warnings", "success"}
        assert required_fields.issubset(field_names)

    def test_parse_result_success(self):
        """Should be able to create a successful ParseResult."""
        episode = EpisodeData(
            content="Test",
            group_id="grp",
            entity_type="type",
            entity_id="id",
            metadata={},
        )
        result = ParseResult(episodes=[episode], warnings=[], success=True)
        assert result.success is True
        assert len(result.episodes) == 1
        assert len(result.warnings) == 0

    def test_parse_result_failure(self):
        """Should be able to create a failed ParseResult."""
        result = ParseResult(
            episodes=[],
            warnings=["Error parsing file"],
            success=False,
        )
        assert result.success is False
        assert len(result.episodes) == 0
        assert "Error parsing file" in result.warnings

    def test_parse_result_with_warnings_but_success(self):
        """ParseResult can have warnings but still be successful."""
        episode = EpisodeData(
            content="Test",
            group_id="grp",
            entity_type="type",
            entity_id="id",
            metadata={},
        )
        result = ParseResult(
            episodes=[episode],
            warnings=["Non-critical warning"],
            success=True,
        )
        assert result.success is True
        assert len(result.warnings) == 1


class TestBaseParser:
    """Tests for BaseParser abstract class."""

    def test_base_parser_is_abstract(self):
        """BaseParser should be an abstract class."""
        from abc import ABC

        assert issubclass(BaseParser, ABC)

    def test_base_parser_cannot_be_instantiated(self):
        """BaseParser should not be instantiatable directly."""
        with pytest.raises(TypeError):
            BaseParser()

    def test_base_parser_has_parser_type_property(self):
        """BaseParser should have abstract parser_type property."""
        assert hasattr(BaseParser, "parser_type")

    def test_base_parser_has_supported_extensions_property(self):
        """BaseParser should have abstract supported_extensions property."""
        assert hasattr(BaseParser, "supported_extensions")

    def test_base_parser_has_parse_method(self):
        """BaseParser should have abstract parse method."""
        assert hasattr(BaseParser, "parse")
        assert callable(getattr(BaseParser, "parse", None))

    def test_base_parser_has_can_parse_method(self):
        """BaseParser should have abstract can_parse method."""
        assert hasattr(BaseParser, "can_parse")
        assert callable(getattr(BaseParser, "can_parse", None))


class TestConcreteParserImplementation:
    """Tests for a concrete parser implementation (to verify the interface)."""

    def test_concrete_parser_can_be_created(self):
        """A concrete parser implementing all abstract methods should work."""

        class MockParser(BaseParser):
            @property
            def parser_type(self) -> str:
                return "mock"

            @property
            def supported_extensions(self) -> list[str]:
                return [".mock", ".test"]

            def parse(self, content: str, file_path: str) -> ParseResult:
                episode = EpisodeData(
                    content=content,
                    group_id="mock-group",
                    entity_type="mock",
                    entity_id=file_path,
                    metadata={"source": "mock"},
                )
                return ParseResult(episodes=[episode], warnings=[], success=True)

            def can_parse(self, content: str, file_path: str) -> bool:
                return file_path.endswith((".mock", ".test"))

        parser = MockParser()
        assert parser.parser_type == "mock"
        assert ".mock" in parser.supported_extensions
        assert parser.can_parse("content", "file.mock") is True
        assert parser.can_parse("content", "file.txt") is False

        result = parser.parse("test content", "file.mock")
        assert result.success is True
        assert len(result.episodes) == 1
        assert result.episodes[0].content == "test content"
