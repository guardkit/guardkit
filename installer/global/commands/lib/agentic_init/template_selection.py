"""Interactive template selection UI for agentic-init command.

This module provides an interactive interface for users to select templates
from the discovered personal and repository templates.
"""

from typing import Optional, List
from .template_discovery import TemplateInfo


def select_template(templates: List[TemplateInfo]) -> Optional[TemplateInfo]:
    """
    Interactive template selection.

    Args:
        templates: Available templates

    Returns:
        Selected template or None if cancelled
    """
    if not templates:
        print("\n❌ No templates available")
        print("\n💡 Tip: Create templates with:")
        print("   • /template-create <name>  (from existing codebase)")
        print("   • /template-init           (from scratch)")
        return None

    print("\n📋 Available Templates:")
    print("=" * 60)

    # Group by source
    personal_templates = [t for t in templates if t.source == "personal"]
    repo_templates = [t for t in templates if t.source == "repository"]

    # Display personal templates first
    if personal_templates:
        print("\n👤 Personal Templates:")
        for i, template in enumerate(personal_templates, 1):
            print(f"\n  [{i}] {template.name} (v{template.version})")
            if template.description:
                print(f"      {template.description}")
            if template.language:
                tech = f"{template.language}"
                if template.frameworks:
                    tech += f" + {', '.join(template.frameworks)}"
                print(f"      {tech}")
            if template.architecture:
                print(f"      Architecture: {template.architecture}")

    # Display repository templates
    if repo_templates:
        print("\n📦 Repository Templates (Built-in):")
        start_idx = len(personal_templates) + 1
        for i, template in enumerate(repo_templates, start_idx):
            print(f"\n  [{i}] {template.name} (v{template.version})")
            if template.description:
                print(f"      {template.description}")
            if template.language:
                tech = f"{template.language}"
                if template.frameworks:
                    tech += f" + {', '.join(template.frameworks)}"
                print(f"      {tech}")

    print("\n" + "=" * 60)

    # Get user selection
    choice = input("\nSelect template (number or name) [or 'q' to quit]: ")

    if choice.lower() == 'q':
        return None

    # Try as number
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(templates):
            return templates[idx]
    except ValueError:
        pass

    # Try as name
    for template in templates:
        if template.name.lower() == choice.lower():
            return template

    print(f"\n❌ Invalid selection: {choice}")
    return select_template(templates)  # Retry


def display_template_info(template: TemplateInfo) -> None:
    """
    Display detailed information about selected template.

    Args:
        template: Template to display
    """
    print(f"\n📋 Template: {template.name}")
    print(f"   Version: {template.version}")

    source_path = "~/.agentecflow/templates/" if template.source == "personal" else "installer/global/templates/"
    print(f"   Source: {template.source} ({source_path})")

    if template.language:
        print(f"   Language: {template.language}")
    if template.frameworks:
        print(f"   Frameworks: {', '.join(template.frameworks)}")
    if template.architecture:
        print(f"   Architecture: {template.architecture}")
    if template.description:
        print(f"   Description: {template.description}")
