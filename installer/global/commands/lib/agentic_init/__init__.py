"""Agentic-init command module.

This module provides template discovery and project initialization functionality
for the agentic-init command, with support for both personal and repository templates.
"""

from .command import agentic_init
from .template_discovery import (
    TemplateDiscovery,
    TemplateInfo,
    discover_templates
)
from .template_selection import (
    select_template,
    display_template_info
)
from .agent_installer import (
    install_template_agents,
    list_template_agents,
    verify_agent_integrity
)

__all__ = [
    "agentic_init",
    "TemplateDiscovery",
    "TemplateInfo",
    "discover_templates",
    "select_template",
    "display_template_info",
    "install_template_agents",
    "list_template_agents",
    "verify_agent_integrity",
]
