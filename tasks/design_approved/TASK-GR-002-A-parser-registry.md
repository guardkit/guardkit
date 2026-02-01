---
complexity: 4
conductor_workspace: gr-mvp-wave6-parsers
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-PRE-003-D
feature_id: FEAT-GR-MVP
id: TASK-GR-002-A
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: design_approved
tags:
- graphiti
- context-addition
- parser
- mvp-phase-2
task_type: feature
title: Create parser registry infrastructure
updated: 2026-01-30 00:00:00+00:00
wave: 6
---

# Task: Create parser registry infrastructure

## Description

Create a parser registry infrastructure that allows different file types to be parsed and seeded to Graphiti. This enables the `guardkit graphiti add-context` command to handle various document types.

## Acceptance Criteria

- [ ] BaseParser abstract class defined
- [ ] ParserRegistry for registering parsers
- [ ] Auto-detection of file type
- [ ] Parser lookup by type name
- [ ] Extensible for future parsers

## Implementation Notes

### Base Parser

```python
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

@dataclass
class ParseResult:
    """Result of parsing a file."""
    episodes: List[EpisodeData]
    warnings: List[str]
    success: bool


@dataclass
class EpisodeData:
    """Data for a single episode."""
    content: str
    group_id: str
    entity_type: str
    entity_id: str
    metadata: dict


class BaseParser(ABC):
    """Base class for content parsers."""

    @property
    @abstractmethod
    def parser_type(self) -> str:
        """Return parser type identifier."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        pass

    @abstractmethod
    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse content and return episodes."""
        pass

    @abstractmethod
    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this parser can handle the content."""
        pass
```

### Parser Registry

```python
class ParserRegistry:
    """Registry for content parsers."""

    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._extension_map: Dict[str, str] = {}

    def register(self, parser: BaseParser) -> None:
        """Register a parser."""
        self._parsers[parser.parser_type] = parser
        for ext in parser.supported_extensions:
            self._extension_map[ext] = parser.parser_type

    def get_parser(self, parser_type: str) -> Optional[BaseParser]:
        """Get parser by type."""
        return self._parsers.get(parser_type)

    def detect_parser(self, file_path: str, content: str) -> Optional[BaseParser]:
        """Auto-detect appropriate parser."""
        # 1. Try extension mapping
        ext = Path(file_path).suffix.lower()
        if ext in self._extension_map:
            parser = self._parsers[self._extension_map[ext]]
            if parser.can_parse(content, file_path):
                return parser

        # 2. Try all parsers
        for parser in self._parsers.values():
            if parser.can_parse(content, file_path):
                return parser

        return None
```

### Files to Create

- `src/guardkit/integrations/graphiti/parsers/__init__.py`
- `src/guardkit/integrations/graphiti/parsers/base.py`
- `src/guardkit/integrations/graphiti/parsers/registry.py`

## Test Requirements

- [ ] Unit tests for registry operations
- [ ] Test parser auto-detection
- [ ] Test extension mapping

## Notes

Foundation for all parsers (GR-002-B through GR-002-D).

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)