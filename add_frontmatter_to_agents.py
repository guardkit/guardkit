#!/usr/bin/env python3
"""
Add YAML frontmatter to template agent files.

This script adds frontmatter to agent files that are missing it,
enabling the CLAUDE.md generator to populate agent metadata.
"""

from pathlib import Path
import re


def extract_metadata_from_content(content: str, filename: str) -> dict:
    """
    Extract metadata from agent content structure.

    Args:
        content: Agent file content
        filename: Agent filename (for name)

    Returns:
        Dictionary with name, description, technologies, priority
    """
    name = Path(filename).stem

    # Extract description from ## Role section
    description = ""
    if "## Role" in content:
        role_section = content.split("## Role")[1].split("##")[0]
        # Get first sentence
        lines = [line.strip() for line in role_section.strip().split('\n') if line.strip()]
        if lines:
            description = lines[0].strip()
            # Remove "You are a " prefix if present
            description = re.sub(r'^You are an? ', '', description, flags=re.IGNORECASE)

    # Extract technologies from ## Expertise section
    technologies = []
    if "## Expertise" in content:
        expertise_section = content.split("## Expertise")[1].split("##")[0]
        # Extract bullet points
        for line in expertise_section.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                # Get first few words as technology
                tech = line.lstrip('- ').split()[0].strip('(')
                if tech and len(tech) > 2:
                    technologies.append(tech)

        # Limit to top 5
        technologies = technologies[:5]

    # If no technologies found, infer from name
    if not technologies:
        name_parts = name.split('-')
        # Capitalize first letter of each part
        technologies = [part.capitalize() for part in name_parts if part != 'specialist'][:3]

    return {
        'name': name,
        'description': description or f"{name.replace('-', ' ').title()} specialist",
        'technologies': technologies,
        'priority': 7  # Default priority
    }


def add_frontmatter_to_file(file_path: Path) -> bool:
    """
    Add YAML frontmatter to agent file if missing.

    Args:
        file_path: Path to agent file

    Returns:
        True if frontmatter was added, False if already present
    """
    content = file_path.read_text(encoding='utf-8')

    # Check if frontmatter already exists
    if content.strip().startswith('---'):
        print(f"  ✓ {file_path.name} already has frontmatter")
        return False

    # Extract metadata from content
    metadata = extract_metadata_from_content(content, file_path.name)

    # Format technologies as YAML list
    tech_yaml = '\n'.join(f"  - {tech}" for tech in metadata['technologies'])

    # Build frontmatter
    frontmatter = f"""---
name: {metadata['name']}
description: {metadata['description']}
priority: {metadata['priority']}
technologies:
{tech_yaml}
---

"""

    # Prepend frontmatter to content
    new_content = frontmatter + content

    # Write back to file
    file_path.write_text(new_content, encoding='utf-8')

    print(f"  ✅ Added frontmatter to {file_path.name}")
    print(f"     Name: {metadata['name']}")
    print(f"     Description: {metadata['description']}")
    print(f"     Technologies: {', '.join(metadata['technologies'])}")

    return True


def main():
    """Main execution."""
    print("Adding YAML frontmatter to template agent files...\n")

    # Find all agent files
    repo_root = Path(__file__).parent
    agent_files = list(repo_root.glob("installer/global/templates/*/agents/*.md"))

    if not agent_files:
        print("❌ No agent files found!")
        return 1

    print(f"Found {len(agent_files)} agent files\n")

    # Process each file
    added_count = 0
    for agent_file in sorted(agent_files):
        template_name = agent_file.parent.parent.name
        print(f"Template: {template_name}")
        if add_frontmatter_to_file(agent_file):
            added_count += 1
        print()

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total files: {len(agent_files)}")
    print(f"  Frontmatter added: {added_count}")
    print(f"  Already had frontmatter: {len(agent_files) - added_count}")
    print(f"{'='*60}\n")

    if added_count > 0:
        print("✅ Frontmatter added successfully!")
        print("\nNext steps:")
        print("1. Run /template-create to regenerate templates")
        print("2. Verify CLAUDE.md has populated agent sections")
        print("3. Commit changes if tests pass")
    else:
        print("✓ All agent files already have frontmatter")

    return 0


if __name__ == "__main__":
    exit(main())
