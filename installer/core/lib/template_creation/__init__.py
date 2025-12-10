"""
Template Creation Module

Provides functionality for creating templates from existing codebases,
including manifest generation, placeholder detection, and template validation.
"""

from .models import (
    TemplateManifest,
    FrameworkInfo,
    PlaceholderInfo,
)
from .manifest_generator import ManifestGenerator

__all__ = [
    "TemplateManifest",
    "FrameworkInfo",
    "PlaceholderInfo",
    "ManifestGenerator",
]
