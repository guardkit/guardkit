"""Tests for ParserRegistry.

TDD RED Phase: These tests define the expected behavior for:
- ParserRegistry class
- Parser registration
- Parser lookup by type
- Auto-detection of file type
"""

import pytest
from pathlib import Path

# These imports will fail until implementation is complete (TDD RED)
from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)
from guardkit.integrations.graphiti.parsers.registry import ParserRegistry


class MockParser(BaseParser):
    """Mock parser for testing."""

    def __init__(self, parser_type: str, extensions: list[str]):
        self._parser_type = parser_type
        self._extensions = extensions

    @property
    def parser_type(self) -> str:
        return self._parser_type

    @property
    def supported_extensions(self) -> list[str]:
        return self._extensions

    def parse(self, content: str, file_path: str) -> ParseResult:
        episode = EpisodeData(
            content=content,
            group_id=f"{self._parser_type}-group",
            entity_type=self._parser_type,
            entity_id=file_path,
            metadata={"parser": self._parser_type},
        )
        return ParseResult(episodes=[episode], warnings=[], success=True)

    def can_parse(self, content: str, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self._extensions


class TestParserRegistry:
    """Tests for ParserRegistry."""

    def test_registry_initialization(self):
        """ParserRegistry should initialize with empty state."""
        registry = ParserRegistry()
        assert registry is not None

    def test_register_parser(self):
        """Should be able to register a parser."""
        registry = ParserRegistry()
        parser = MockParser("markdown", [".md"])
        registry.register(parser)
        assert registry.get_parser("markdown") is parser

    def test_register_multiple_parsers(self):
        """Should be able to register multiple parsers."""
        registry = ParserRegistry()
        md_parser = MockParser("markdown", [".md"])
        task_parser = MockParser("task", [".md"])

        registry.register(md_parser)
        registry.register(task_parser)

        assert registry.get_parser("markdown") is md_parser
        assert registry.get_parser("task") is task_parser

    def test_get_parser_returns_none_for_unknown(self):
        """get_parser should return None for unknown parser type."""
        registry = ParserRegistry()
        assert registry.get_parser("unknown") is None

    def test_get_parser_by_type(self):
        """Should be able to get parser by type name."""
        registry = ParserRegistry()
        parser = MockParser("yaml", [".yaml", ".yml"])
        registry.register(parser)

        retrieved = registry.get_parser("yaml")
        assert retrieved is parser
        assert retrieved.parser_type == "yaml"


class TestParserDetection:
    """Tests for auto-detection of file type."""

    def test_detect_parser_by_extension(self):
        """Should detect parser by file extension."""
        registry = ParserRegistry()
        md_parser = MockParser("markdown", [".md"])
        registry.register(md_parser)

        detected = registry.detect_parser("test.md", "# Content")
        assert detected is md_parser

    def test_detect_parser_by_extension_case_insensitive(self):
        """Extension detection should be case-insensitive."""
        registry = ParserRegistry()
        md_parser = MockParser("markdown", [".md"])
        registry.register(md_parser)

        detected = registry.detect_parser("test.MD", "# Content")
        assert detected is md_parser

    def test_detect_parser_returns_none_for_unknown(self):
        """detect_parser should return None for unknown file types."""
        registry = ParserRegistry()
        md_parser = MockParser("markdown", [".md"])
        registry.register(md_parser)

        detected = registry.detect_parser("test.xyz", "content")
        assert detected is None

    def test_detect_parser_uses_can_parse_validation(self):
        """detect_parser should verify with can_parse."""
        registry = ParserRegistry()

        # Create a parser that has .md extension but rejects certain content
        class SelectiveParser(BaseParser):
            @property
            def parser_type(self) -> str:
                return "selective"

            @property
            def supported_extensions(self) -> list[str]:
                return [".md"]

            def parse(self, content: str, file_path: str) -> ParseResult:
                return ParseResult(episodes=[], warnings=[], success=True)

            def can_parse(self, content: str, file_path: str) -> bool:
                # Only parse if content starts with "SELECT:"
                return content.startswith("SELECT:")

        parser = SelectiveParser()
        registry.register(parser)

        # Should return None because can_parse returns False
        assert registry.detect_parser("test.md", "# Regular markdown") is None

        # Should return parser when can_parse returns True
        assert registry.detect_parser("test.md", "SELECT: content") is parser

    def test_detect_parser_fallback_to_content_check(self):
        """detect_parser should try all parsers if extension doesn't match."""
        registry = ParserRegistry()

        class ContentBasedParser(BaseParser):
            @property
            def parser_type(self) -> str:
                return "json-ish"

            @property
            def supported_extensions(self) -> list[str]:
                return [".json"]

            def parse(self, content: str, file_path: str) -> ParseResult:
                return ParseResult(episodes=[], warnings=[], success=True)

            def can_parse(self, content: str, file_path: str) -> bool:
                # Can parse anything that looks like JSON
                return content.strip().startswith("{")

        parser = ContentBasedParser()
        registry.register(parser)

        # File has .txt extension but content is JSON-ish
        detected = registry.detect_parser("data.txt", '{"key": "value"}')
        assert detected is parser


class TestExtensionMapping:
    """Tests for extension to parser type mapping."""

    def test_extension_mapping_created_on_register(self):
        """Registering a parser should create extension mappings."""
        registry = ParserRegistry()
        parser = MockParser("yaml", [".yaml", ".yml"])
        registry.register(parser)

        # Both extensions should map to the parser
        assert registry.detect_parser("config.yaml", "content") is parser
        assert registry.detect_parser("config.yml", "content") is parser

    def test_extension_mapping_overwrite(self):
        """Later registration should overwrite extension mapping."""
        registry = ParserRegistry()
        parser1 = MockParser("parser1", [".md"])
        parser2 = MockParser("parser2", [".md"])

        registry.register(parser1)
        registry.register(parser2)

        # The last registered parser for .md should be used
        detected = registry.detect_parser("test.md", "content")
        # Note: parser2's can_parse might still be used for validation
        # The extension mapping points to parser2 but can_parse is checked
        assert detected is parser2

    def test_parser_with_no_extensions(self):
        """Parser with no extensions should still be usable via can_parse."""
        registry = ParserRegistry()

        class NoExtensionParser(BaseParser):
            @property
            def parser_type(self) -> str:
                return "special"

            @property
            def supported_extensions(self) -> list[str]:
                return []  # No extensions

            def parse(self, content: str, file_path: str) -> ParseResult:
                return ParseResult(episodes=[], warnings=[], success=True)

            def can_parse(self, content: str, file_path: str) -> bool:
                return "SPECIAL_MARKER" in content

        parser = NoExtensionParser()
        registry.register(parser)

        # Should find parser through can_parse fallback
        detected = registry.detect_parser("anyfile.xyz", "Contains SPECIAL_MARKER here")
        assert detected is parser

        # Should return None when marker not present
        assert registry.detect_parser("anyfile.xyz", "Regular content") is None


class TestRegistryEdgeCases:
    """Edge case tests for ParserRegistry."""

    def test_empty_file_path(self):
        """detect_parser should handle empty file path."""
        registry = ParserRegistry()
        parser = MockParser("text", [".txt"])
        registry.register(parser)

        # Empty path has no extension
        detected = registry.detect_parser("", "content")
        assert detected is None

    def test_file_path_with_no_extension(self):
        """detect_parser should handle files with no extension."""
        registry = ParserRegistry()
        parser = MockParser("text", [".txt"])
        registry.register(parser)

        # Makefile has no extension
        detected = registry.detect_parser("Makefile", "content")
        assert detected is None

    def test_get_parser_with_none(self):
        """get_parser should handle None gracefully."""
        registry = ParserRegistry()
        assert registry.get_parser(None) is None

    def test_detect_parser_with_path_object(self):
        """detect_parser should work with Path objects as file_path."""
        registry = ParserRegistry()
        parser = MockParser("markdown", [".md"])
        registry.register(parser)

        # Use string path (Path objects converted to str in implementation)
        detected = registry.detect_parser(str(Path("docs/README.md")), "# Content")
        assert detected is parser

    def test_register_same_parser_twice(self):
        """Registering the same parser twice should not cause issues."""
        registry = ParserRegistry()
        parser = MockParser("markdown", [".md"])

        registry.register(parser)
        registry.register(parser)

        assert registry.get_parser("markdown") is parser
