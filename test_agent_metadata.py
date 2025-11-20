#!/usr/bin/env python3
"""Test that CLAUDE.md generator can read agent frontmatter."""

from pathlib import Path
import sys
import yaml


def test_agent_frontmatter(agent_file: Path) -> bool:
    """Test if agent file has valid frontmatter."""
    try:
        content = agent_file.read_text(encoding='utf-8')

        # Check frontmatter exists
        if not content.startswith('---'):
            print(f"  ❌ No frontmatter: {agent_file.name}")
            return False

        # Extract and parse frontmatter
        parts = content.split('---', 2)
        if len(parts) < 3:
            print(f"  ❌ Invalid frontmatter format: {agent_file.name}")
            return False

        metadata = yaml.safe_load(parts[1])

        # Verify required fields
        required_fields = ['name', 'description', 'priority', 'technologies']
        missing = [f for f in required_fields if f not in metadata]

        if missing:
            print(f"  ❌ Missing fields {missing}: {agent_file.name}")
            return False

        # Verify field types
        if not isinstance(metadata['name'], str):
            print(f"  ❌ 'name' must be string: {agent_file.name}")
            return False

        if not isinstance(metadata['description'], str):
            print(f"  ❌ 'description' must be string: {agent_file.name}")
            return False

        if not isinstance(metadata['priority'], int):
            print(f"  ❌ 'priority' must be int: {agent_file.name}")
            return False

        if not isinstance(metadata['technologies'], list):
            print(f"  ❌ 'technologies' must be list: {agent_file.name}")
            return False

        print(f"  ✅ {agent_file.name}")
        print(f"     Name: {metadata['name']}")
        print(f"     Description: {metadata['description'][:60]}...")
        print(f"     Technologies: {', '.join(metadata['technologies'][:3])}")

        return True

    except Exception as e:
        print(f"  ❌ Error parsing {agent_file.name}: {e}")
        return False


def main():
    """Main execution."""
    print("Testing agent frontmatter...\n")

    # Find all agent files
    repo_root = Path(__file__).parent
    agent_files = list(repo_root.glob("installer/global/templates/*/agents/*.md"))

    if not agent_files:
        print("❌ No agent files found!")
        return 1

    print(f"Found {len(agent_files)} agent files\n")

    # Test each file
    passed = 0
    failed = 0

    for agent_file in sorted(agent_files):
        template_name = agent_file.parent.parent.name
        print(f"Template: {template_name}")
        if test_agent_frontmatter(agent_file):
            passed += 1
        else:
            failed += 1
        print()

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total files: {len(agent_files)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"{'='*60}\n")

    if failed == 0:
        print("✅ All agent files have valid frontmatter!")
        return 0
    else:
        print(f"❌ {failed} agent files have issues")
        return 1


if __name__ == "__main__":
    exit(main())
