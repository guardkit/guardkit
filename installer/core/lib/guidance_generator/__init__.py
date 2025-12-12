"""
Guidance Generator Module

Generates slim guidance files in .claude/rules/guidance/ from full agent files.

Guidance files are derived summaries (<3KB) that load automatically on path match,
while agent files are the source of truth (6-12KB) loaded when Task tool invokes specialist.
"""

from .generator import generate_guidance_from_agent, save_guidance
from .extractor import extract_boundaries, extract_capability_summary
from .path_patterns import generate_path_patterns
from .validator import validate_guidance_size

__all__ = [
    "generate_guidance_from_agent",
    "save_guidance",
    "extract_boundaries",
    "extract_capability_summary",
    "generate_path_patterns",
    "validate_guidance_size",
]
