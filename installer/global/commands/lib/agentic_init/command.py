"""Main command module for agentic-init.

This module provides the main entry point for the agentic-init command,
which initializes projects using templates discovered from personal and
repository locations.
"""

from pathlib import Path
from typing import Optional
import shutil

from .template_discovery import discover_templates, TemplateDiscovery
from .template_selection import select_template, display_template_info
from .agent_installer import install_template_agents


def agentic_init(
    template_name: Optional[str] = None,
    project_path: Optional[Path] = None
) -> bool:
    """
    Initialize project with template.

    Args:
        template_name: Template name (if not provided, show selection UI)
        project_path: Path to initialize (default: current directory)

    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 60)
    print("  Agentic Init - Project Initialization")
    print("=" * 60)

    # Use current directory if not specified
    if project_path is None:
        project_path = Path.cwd()

    # Step 1: Discover templates
    print("\n" + "=" * 60)
    print("  Phase 1: Template Discovery")
    print("=" * 60 + "\n")

    templates = discover_templates()

    if not templates:
        print("\n❌ No templates found")
        print("\n💡 Tip: Create templates with:")
        print("   • /template-create <name>  (from existing codebase)")
        print("   • /template-init           (from scratch)")
        return False

    # Step 2: Select template
    print("\n" + "=" * 60)
    print("  Phase 2: Template Selection")
    print("=" * 60)

    if template_name:
        # Use specified template
        discovery = TemplateDiscovery()
        template = discovery.find_by_name(templates, template_name)
        if not template:
            print(f"\n❌ Template '{template_name}' not found")
            print(f"\n💡 Available templates:")
            for t in templates:
                print(f"   • {t.name} ({t.source})")
            return False
    else:
        # Interactive selection
        template = select_template(templates)
        if not template:
            print("\n❌ No template selected")
            return False

    # Step 3: Display template info
    print("\n" + "=" * 60)
    print("  Phase 3: Template Information")
    print("=" * 60)

    display_template_info(template)

    # Step 4: Copy template structure
    print("\n" + "=" * 60)
    print("  Phase 4: Project Structure")
    print("=" * 60 + "\n")

    if not _copy_template_structure(template, project_path):
        return False

    # Step 5: Install agents
    print("\n" + "=" * 60)
    print("  Phase 5: Agent Installation")
    print("=" * 60)

    install_template_agents(template, project_path)

    # Step 6: Finalize
    print("\n" + "=" * 60)
    print("  Initialization Complete")
    print("=" * 60 + "\n")

    print(f"✅ Project initialized successfully!")
    print(f"   Template: {template.name}")
    print(f"   Location: {project_path}")

    return True


def _copy_template_structure(
    template: TemplateInfo,
    project_path: Path
) -> bool:
    """
    Copy template structure to project.

    Args:
        template: Selected template
        project_path: Destination path

    Returns:
        True if successful, False otherwise
    """
    print("📂 Copying template structure...")

    # Create .claude directory
    claude_dir = project_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Copy manifest.json
    manifest_src = template.source_path / "manifest.json"
    if manifest_src.exists():
        shutil.copy(manifest_src, claude_dir / "manifest.json")
        print("  ✓ Copied manifest.json")

    # Copy settings.json
    settings_src = template.source_path / "settings.json"
    if settings_src.exists():
        shutil.copy(settings_src, claude_dir / "settings.json")
        print("  ✓ Copied settings.json")

    # Copy CLAUDE.md
    claude_md_src = template.source_path / "CLAUDE.md"
    if claude_md_src.exists():
        shutil.copy(claude_md_src, project_path / "CLAUDE.md")
        print("  ✓ Copied CLAUDE.md")

    # Copy templates directory if exists
    templates_src = template.source_path / "templates"
    if templates_src.exists() and templates_src.is_dir():
        templates_dst = project_path / "templates"
        if templates_dst.exists():
            print(f"  ⚠️  Templates directory already exists, skipping")
        else:
            shutil.copytree(templates_src, templates_dst)
            print("  ✓ Copied code templates")

    print("\n✅ Template structure copied successfully")
    return True


def main():
    """Command-line entry point."""
    import sys

    template_name = None
    if len(sys.argv) > 1:
        template_name = sys.argv[1]

    success = agentic_init(template_name)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
