"""
Template Generation Library

Provides components for generating template files from codebase analysis,
including manifest.json, settings.json, CLAUDE.md, and code templates.
"""

from .models import TemplateClaude
from .claude_md_generator import ClaudeMdGenerator

__all__ = [
    'TemplateClaude',
    'ClaudeMdGenerator',
]
